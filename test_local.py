import os, tempfile, subprocess, zipfile, stat, sys, pathlib
from sonic import run_upload, UploadError

def g(*a): return subprocess.check_output(['git',*a],stderr=subprocess.DEVNULL).decode().strip()
with tempfile.TemporaryDirectory() as tmp:
    root=pathlib.Path(tmp); remote=root/'remote.git'; g('init','--bare','--initial-branch=main',str(remote)); z=root/'source.zip'
    with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED) as f:
        for i in range(2100): f.writestr(f'root/src/{i}.txt',f'file {i}\n')
        f.writestr('root/large.bin',os.urandom(2*1024*1024))
        sy=zipfile.ZipInfo('root/snapcraft.yaml');sy.create_system=3;sy.external_attr=(stat.S_IFLNK|0o777)<<16;f.writestr(sy,'src/1.txt')
        ex=zipfile.ZipInfo('root/run.sh');ex.create_system=3;ex.external_attr=(stat.S_IFREG|0o755)<<16;f.writestr(ex,'echo hi\n')
        f.writestr('root/空 文件.txt','hello')
        f.writestr('root/empty','')
    cfg=dict(owner='example',repo='example',branch='main',parallel=8,threshold=1048576,strip=True,overwrite=True,message='first')
    states=[]; start=__import__('time').monotonic()
    commit=run_upload(z,cfg,'',lambda **kw:states.append(kw),str(remote)); assert g('--git-dir='+str(remote),'rev-parse','main')==commit
    assert len(g('--git-dir='+str(remote),'ls-tree','-r','main').splitlines())==2105
    assert '120000' in g('--git-dir='+str(remote),'ls-tree','main','snapcraft.yaml')
    assert '100755' in g('--git-dir='+str(remote),'ls-tree','main','run.sh')
    heavy=next(i for i,s in enumerate(states) if s.get('phase')=='heavy'); assert states[heavy]['done']==2104 and not any(s.get('phase')=='push' for s in states[:heavy])
    print('First native push: 2105 files, %.2fs'%(__import__('time').monotonic()-start))
    with zipfile.ZipFile(z,'w') as f: f.writestr('root/src/1.txt','changed')
    cfg['strip']=True; cfg['message']='second'; commit2=run_upload(z,cfg,'',lambda **kw:None,str(remote)); assert commit!=commit2
    assert g('--git-dir='+str(remote),'show','main:src/1.txt')=='changed'
    assert len(g('--git-dir='+str(remote),'ls-tree','-r','main').splitlines())==2105
    assert run_upload(z,cfg,'',lambda **kw:None,str(remote))==commit2
    with zipfile.ZipFile(z,'w') as f: f.writestr('root/src/1.txt','reject')
    cfg['overwrite']=False
    try: run_upload(z,cfg,'',lambda **kw:None,str(remote)); raise AssertionError('overwrite not rejected')
    except UploadError: pass
    assert g('--git-dir='+str(remote),'rev-parse','main')==commit2
    print('PASS overwrite, preserve other files, identical skip, reject overwrite, symlink, executable, unicode, verified remote.')
