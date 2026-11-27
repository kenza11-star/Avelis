#!/usr/bin/env python3
"""Sonic V6: local ZIP -> native Git pack -> verified push. Python stdlib only."""
import hashlib, json, os, re, secrets, shutil, stat, subprocess, tempfile, threading, time, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor

MAX_ZIP = 1_000_000_000
MAX_FILE = 100 * 1024**2
MAX_EXPANDED = 2 * 1024**3
MAX_ENTRIES = 200_000
CHUNK = 256 * 1024
REF = 'refs/heads/sonic-import'

class UploadError(Exception): pass

def validate_path(name):
    parts = name.split('/')
    if any(not x or x in ('.','..') or x.rstrip(' .').lower() in ('.git','git~1') or '\\' in x or ':' in x or any(ord(c)<32 or ord(c)==127 for c in x) for x in parts):
        raise UploadError('Path ZIP tidak aman/tidak didukung: '+repr(name))
    return name

def scan(z, strip, prefix):
    infos = z.infolist()
    if len(infos)>MAX_ENTRIES: raise UploadError('Terlalu banyak entri ZIP (maks. 200.000).')
    entries=[]; total=0; seen=set()
    for i in infos:
        raw=i.orig_filename
        if '\x00' in raw: raise UploadError('Nama ZIP mengandung NUL.')
        name=validate_path(raw.rstrip('/') if i.is_dir() else raw)
        if i.is_dir(): continue
        if i.flag_bits & 1: raise UploadError('ZIP terenkripsi tidak didukung.')
        if i.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED,zipfile.ZIP_BZIP2,zipfile.ZIP_LZMA): raise UploadError('Metode kompresi tidak didukung: '+name)
        mode=(i.external_attr>>16) if i.create_system==3 else 0
        typ=stat.S_IFMT(mode)
        if typ not in (0,stat.S_IFREG,stat.S_IFLNK): raise UploadError('Tipe file khusus tidak didukung: '+name)
        if i.file_size>MAX_FILE: raise UploadError('File melebihi 100 MiB (butuh Git LFS): '+name)
        if typ==stat.S_IFLNK and i.file_size>4096: raise UploadError('Target symlink terlalu panjang: '+name)
        total+=i.file_size
        if total>MAX_EXPANDED: raise UploadError('Isi ZIP melebihi 2 GiB.')
        entries.append((name,i,'120000' if typ==stat.S_IFLNK else '100755' if mode&0o111 else '100644'))
    if not entries: raise UploadError('ZIP tidak memiliki file.')
    root=entries[0][0].split('/')[0]
    if strip and all(n.startswith(root+'/') for n,_,_ in entries): entries=[(n[len(root)+1:],i,m) for n,i,m in entries]
    if prefix: prefix=validate_path(prefix.strip('/'))+'/'
    entries=[(validate_path(prefix+n),i,m) for n,i,m in entries]
    for n,_,_ in entries:
        if n in seen: raise UploadError('Path duplikat: '+n)
        seen.add(n)
    for n in seen:
        parts=n.split('/')
        if any('/'.join(parts[:j]) in seen for j in range(1,len(parts))): raise UploadError('Konflik file/folder: '+n)
    return sorted(entries,key=lambda e:(e[1].file_size,e[0]))

def qpath(n):
    return b'"'+b''.join(bytes([c]) if 32<=c<127 and c not in (34,92) else ('\\%03o'%c).encode() for c in n.encode('utf-8'))+b'"'

def tree(git, ref):
    result={}
    for line in git('ls-tree','-rz',ref).split(b'\0'):
        if not line: continue
        meta,name=line.split(b'\t',1); mode,typ,sha=meta.decode().split()
        result[name.decode('utf-8','surrogateescape')]=(mode,sha)
    return result

def sha_blob(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def run_upload(zip_path, cfg, token, report, remote_override=None):
    owner,repo,branch=cfg['owner'],cfg['repo'],cfg.get('branch','').strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',owner) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',repo) or repo in ('.','..'): raise UploadError('Owner/repository tidak valid.')
    if cfg['parallel'] not in (8,16): raise UploadError('Parallel harus 8 atau 16.')
    threshold=int(cfg.get('threshold',1048576))
    if threshold not in (262144,1048576,4194304): raise UploadError('Threshold tidak valid.')
    message=cfg.get('message','Update source code').strip()
    if not message or len(message)>2000: raise UploadError('Pesan commit wajib diisi, maks. 2.000 karakter.')
    with zipfile.ZipFile(zip_path) as z, tempfile.TemporaryDirectory(prefix='sonic-git-') as td:
        entries=scan(z,cfg.get('strip',True),cfg.get('prefix',''))
        light=[e for e in entries if e[1].file_size<threshold]; heavy=[e for e in entries if e[1].file_size>=threshold]
        report(phase='scan',total=len(entries),light=len(light),heavy=len(heavy),done=0,changed=0,detail='Memeriksa ZIP selesai.')
        basepath=Path(td); gitdir=basepath/'repo.git'; ask=basepath/'askpass.sh'
        ask.write_text('#!'+(shutil.which('sh') or '/bin/sh')+'\ncase "$1" in *Username*) printf "%s\\n" x-access-token;; *) printf "%s\\n" "$SONIC_TOKEN";; esac\n'); ask.chmod(0o700)
        env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_TERMINAL_PROMPT='0',GIT_ASKPASS=str(ask),SONIC_TOKEN=token,LC_ALL='C')
        remote=remote_override or f'https://github.com/{owner}/{repo}.git'
        def safe(s): return s.replace(token,'[REDACTED]') if token else s
        def git(*args, data=None):
            cmd=['git','-c','credential.helper=','-c','http.followRedirects=false','-c','core.compression=1','-c',f'pack.threads={cfg["parallel"]}','-c','pack.windowMemory=8m','-C',str(gitdir),*args]
            p=subprocess.run(cmd,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
            if p.returncode: raise UploadError(safe(p.stderr.decode(errors='replace').strip()) or 'Git gagal: '+args[0])
            return p.stdout
        gitdir.mkdir(); git('init','--bare','--object-format=sha1');
        if branch: git('check-ref-format','--branch',branch)
        report(phase='connect',detail='Menghubungkan Git remote…')
        refs=git('ls-remote','--symref',remote,'HEAD','refs/heads/*').decode().splitlines()
        heads={}; default=None
        for line in refs:
            a,b=line.split('\t',1)
            if a.startswith('ref: refs/heads/') and b=='HEAD': default=a[len('ref: refs/heads/'):]
            elif b.startswith('refs/heads/'): heads[b[len('refs/heads/'):]]=a
        branch=branch or default or ('main' if not heads else next(iter(heads)))
        git('check-ref-format','--branch',branch)
        if heads and branch not in heads: raise UploadError('Branch tidak ditemukan. Pilih branch yang sudah ada.')
        base=heads.get(branch); old={}
        if base:
            report(phase='fetch',detail='Mengambil snapshot branch (tanpa checkout)…')
            git('fetch','--depth=1','--no-tags',remote,'refs/heads/'+branch)
            base=git('rev-parse','FETCH_HEAD').decode().strip(); old=tree(git,base)
        # Preserve unrelated existing files. Never implicitly replace a directory or submodule.
        paths=set(old); dirs=set()
        for n in paths:
            parts=n.split('/'); dirs.update('/'.join(parts[:j]) for j in range(1,len(parts)))
        for n,_,_ in entries:
            parts=n.split('/')
            if n in dirs or any('/'.join(parts[:j]) in paths for j in range(1,len(parts))) or (n in old and old[n][0]=='160000'):
                raise UploadError('Konflik file/folder/submodule di repo: '+n)
        expected={}; done=changed=0; started=time.monotonic(); last=0
        err=basepath/'import.log'
        cmd=['git','-c','core.compression=1','-C',str(gitdir),'fast-import','--quiet','--done','--depth=10','--max-pack-size=1g']
        with err.open('wb') as ef:
            p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=ef,env=env)
            w=p.stdin
            try:
                def put(b): w.write(b)
                msg=message.encode(); put(b'commit '+REF.encode()+b'\ncommitter Sonic Uploader <sonic-uploader@users.noreply.github.com> '+str(int(time.time())).encode()+b' +0000\ndata '+str(len(msg)).encode()+b'\n'+msg+b'\n')
                if base: put(b'from '+base.encode()+b'\n')
                def update(n,mode,sha):
                    nonlocal done,changed,last
                    expected[n]=(mode,sha); done+=1
                    if old.get(n)!=(mode,sha): changed+=1
                    now=time.monotonic()
                    if now-last>.15 or done==len(entries):
                        report(done=done,changed=changed,rate=round(done/max(.001,now-started),1),detail=n); last=now
                def read_small(e):
                    n,i,mode=e; data=z.read(i); return n,mode,data,sha_blob(data)
                # Bound buffered small-file data, use at most 8 decompression workers.
                report(phase='light',detail='Memproses semua file ringan dahulu…')
                with ThreadPoolExecutor(max_workers=min(8,cfg['parallel'])) as pool:
                    batch=[]; size=0
                    def flush():
                        for n,mode,data,sha in pool.map(read_small,batch):
                            if old.get(n)!=(mode,sha):
                                if n in old and not cfg.get('overwrite',True): raise UploadError('File berbeda sudah ada: '+n)
                                put(b'M '+mode.encode()+b' inline '+qpath(n)+b'\ndata '+str(len(data)).encode()+b'\n'+data+b'\n')
                            update(n,mode,sha)
                    for e in light:
                        if batch and (len(batch)>=128 or size+e[1].file_size>8*1024**2): flush(); batch=[]; size=0
                        batch.append(e); size+=e[1].file_size
                    if batch: flush()
                report(phase='heavy',done=done,changed=changed,detail='File ringan selesai. Memproses file berat…')
                for n,i,mode in heavy:
                    # Stream heavy bytes, no Base64 and no full-file allocation.
                    # When overwrite is disabled, hash first to decide whether to reject.
                    if n in old and not cfg.get('overwrite',True):
                        h=hashlib.sha1(b'blob '+str(i.file_size).encode()+b'\0')
                        with z.open(i) as f:
                            while chunk:=f.read(CHUNK): h.update(chunk)
                        sha=h.hexdigest()
                        if old[n]!=(mode,sha): raise UploadError('File berbeda sudah ada: '+n)
                        update(n,mode,sha); continue
                    h=hashlib.sha1(b'blob '+str(i.file_size).encode()+b'\0'); put(b'M '+mode.encode()+b' inline '+qpath(n)+b'\ndata '+str(i.file_size).encode()+b'\n')
                    with z.open(i) as f:
                        while chunk:=f.read(CHUNK): h.update(chunk); put(chunk)
                    put(b'\n'); update(n,mode,h.hexdigest())
                put(b'\ndone\n'); w.close()
                if p.wait()!=0: raise UploadError('Git fast-import gagal: '+safe(err.read_text(errors='replace'))[-2000:])
            except BaseException:
                if p.poll() is None: p.kill()
                try: w.close()
                except (BrokenPipeError,OSError): pass
                p.wait(); raise
        report(phase='verify',detail='Memverifikasi SHA dan mode seluruh file…')
        commit=git('rev-parse',REF).decode().strip(); new=tree(git,commit)
        if any(new.get(n)!=v for n,v in expected.items()) or any(new.get(n)!=v for n,v in old.items() if n not in expected): raise UploadError('Verifikasi tree gagal. Tidak melakukan push.')
        if not changed and base:
            commit=base
        else:
            report(phase='push',detail='Mengirim pack Git ke remote…')
            # Stream Git stderr progress without collecting the pack in memory.
            cmd=['git','-c','credential.helper=','-c','http.followRedirects=false','-c','core.compression=1','-c',f'pack.threads={cfg["parallel"]}','-c','pack.windowMemory=8m','-C',str(gitdir),'push','--progress',remote,REF+':refs/heads/'+branch]
            with tempfile.TemporaryFile() as output:
                proc=subprocess.Popen(cmd,stdout=output,stderr=subprocess.PIPE,env=env)
                buf=bytearray(); tail=[]
                for byte in iter(lambda:proc.stderr.read(1),b''):
                    if byte in (b'\r',b'\n'):
                        if buf:
                            line=safe(buf.decode(errors='replace')); tail.append(line); tail=tail[-12:]; report(detail=line); buf.clear()
                    elif len(buf)<4096: buf.extend(byte)
                if proc.wait()!=0: raise UploadError('Push gagal: '+'\n'.join(tail))
        report(phase='remote-verify',detail='Memastikan SHA commit pada branch remote…')
        actual=git('ls-remote',remote,'refs/heads/'+branch).decode().split()
        if not actual or actual[0]!=commit: raise UploadError('SHA branch remote berbeda. Periksa repo; tidak mengklaim sukses.')
        report(phase='success',detail='Commit terverifikasi di remote.',commit=commit,branch=branch,url=f'https://github.com/{owner}/{repo}/commit/{commit}',done=len(entries),changed=changed)
        return commit

SESSION=secrets.token_urlsafe(32); LOCK=threading.Lock(); STATE={'phase':'idle'}; BUSY=False

def report(**kw):
    with LOCK: STATE.update(kw)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,data,kind='application/json; charset=utf-8'):
        if not isinstance(data,bytes): data=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'"); self.end_headers(); self.wfile.write(data)
    def allowed(self):
        host=self.headers.get('Host',''); origin=self.headers.get('Origin')
        return host==f'127.0.0.1:{self.server.server_port}' and (origin is None or origin=='http://'+host)
    def authorized(self): return self.allowed() and secrets.compare_digest(self.headers.get('X-Sonic-Session',''),SESSION)
    def do_GET(self):
        if not self.allowed(): return self.reply(403,{'error':'Forbidden'})
        if self.path=='/': return self.reply(200,Path(__file__).with_name('index.html').read_text().replace('__SONIC_SESSION__',SESSION).encode(),'text/html; charset=utf-8')
        if self.path=='/status' and self.authorized():
            with LOCK: data=dict(STATE)
            return self.reply(200,data)
        self.reply(404,{'error':'Not found'})
    def do_POST(self):
        global BUSY
        if self.path!='/upload' or not self.authorized(): return self.reply(403,{'error':'Forbidden'})
        try:
            length=int(self.headers.get('Content-Length','0')); cfg=json.loads(unquote(self.headers.get('X-Sonic-Config',''))); token=self.headers.get('X-GitHub-Token','')
            if not 0<length<=MAX_ZIP or not token or len(token)>512 or not isinstance(cfg,dict): raise ValueError()
        except (ValueError,TypeError): return self.reply(400,{'error':'ZIP, token, atau konfigurasi tidak valid.'})
        with LOCK:
            if BUSY: return self.reply(409,{'error':'Upload sedang berjalan.'})
            BUSY=True; STATE.clear(); STATE.update(phase='receive',done=0,total=0,detail='Menerima ZIP di localhost…')
        folder=None
        try:
            folder=tempfile.mkdtemp(prefix='sonic-zip-'); path=Path(folder)/'input.zip'
            if shutil.disk_usage(folder).free<length+64*1024**2: raise UploadError('Penyimpanan tidak cukup untuk ZIP.')
            self.connection.settimeout(120)
            with path.open('wb') as f:
                remaining=length
                while remaining:
                    chunk=self.rfile.read(min(1024**2,remaining))
                    if not chunk: raise UploadError('Transfer ZIP terputus.')
                    f.write(chunk); remaining-=len(chunk)
            def task():
                global BUSY
                try: run_upload(path,cfg,token,report)
                except Exception as e: report(phase='error',detail=str(e).replace(token,'[REDACTED]'))
                finally:
                    shutil.rmtree(folder,ignore_errors=True)
                    with LOCK: BUSY=False
            threading.Thread(target=task,daemon=True).start()
        except Exception as e:
            if folder: shutil.rmtree(folder,ignore_errors=True)
            report(phase='error',detail=str(e).replace(token,'[REDACTED]'))
            with LOCK: BUSY=False
            return self.reply(400,{'error':str(e).replace(token,'[REDACTED]')})
        self.reply(202,{'accepted':True})

if __name__=='__main__':
    if not shutil.which('git'): raise SystemExit('Install Git: pkg install git')
    server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    print('Sonic V6 Native: http://127.0.0.1:8765\nCtrl+C untuk berhenti.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
