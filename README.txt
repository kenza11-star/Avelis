GITHUB SONIC UPLOADER V6 — NATIVE

Android / Termux
1. pkg install python git unzip -y
2. termux-setup-storage (allow storage if prompted)
3. mkdir -p ~/sonic-v6
4. unzip -o ~/storage/downloads/GitHub-Sonic-Uploader-V6-Native.zip -d ~/sonic-v6
5. cd ~/sonic-v6
6. python sonic.py
7. Open http://127.0.0.1:8765 in Chrome.
   Keep Termux running while the upload runs. Ctrl+C stops the server.
   The HTML is served locally; do not open index.html directly.

Use a GitHub token limited to the intended repository, with Contents: Read and write.
Changes to .github/workflows may require Workflows: Read and write as well.
Review the ZIP for credentials or private data before pushing. Token is not saved by the app.
No external backend or Python dependencies. The local HTTP server listens only on 127.0.0.1.

Native Git fast-import builds a commit without extracting to a working tree. All light
files are processed before heavy files. The archive is streamed from the local browser to
Termux, then Git pushes a binary pack in one operation. 8/16 selects Git packing threads,
not separate network uploads. Up to 8 threads prepare small files. Existing unrelated
files are preserved. Directory/file conflicts stop the job rather than deleting files.
Existing branch snapshots are fetched before import. Empty repositories are supported;
if no branch is specified, the remote default is used (main for a new empty repo).
No force push. Success requires local tree validation and a matching remote commit SHA.

Limits: ZIP <= 1,000,000,000 bytes, expanded contents <= 2 GiB, 200,000 entries,
individual file <= 100 MiB. ZIP64 and standard Python-supported compression methods
(Store/Deflate/BZIP2/LZMA); no encryption, Git LFS, or unusual special files. Empty
folders are not tracked by Git. Space for ZIP and Git objects is needed; existing branch
snapshot size may add to disk usage. GitHub policies can reject pushes. GitHub's 2 GiB
push limit still applies. Real speed depends on device, repo and network. No guaranteed
5x speedup. Do not stop during push unless necessary; check the branch afterward.

Local test: python test_local.py (does not contact GitHub).
