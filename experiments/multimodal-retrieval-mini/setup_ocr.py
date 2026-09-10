"""Download Debian Trixie amd64 OCR packages into project cache; no sudo."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2] / 'cache/tesseract'
PACKAGES = ['tesseract-ocr=5.5.0-1+b1', 'libtesseract5=5.5.0-1+b1',
            'libleptonica6=1.84.1-4', 'tesseract-ocr-eng=1:4.1.0-2', 'tesseract-ocr-osd=1:4.1.0-2']

def main():
    packages = ROOT / 'packages'
    packages.mkdir(parents=True, exist_ok=True)
    if subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip() != 'amd64':
        raise RuntimeError('This local setup is for Debian amd64; install Tesseract with your platform package manager instead.')
    subprocess.run(['apt-get', 'download', *PACKAGES], cwd=packages, check=True)
    records = []
    for path in sorted(packages.glob('*.deb')):
        subprocess.run(['dpkg-deb', '-x', str(path), str(ROOT / 'root')], check=True)
        records.append({'name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (ROOT / 'packages.json').write_text(json.dumps(records, indent=2) + '\n')
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(ROOT / 'root/usr/lib/x86_64-linux-gnu')
    env['TESSDATA_PREFIX'] = str(ROOT / 'root/usr/share/tesseract-ocr/5/tessdata')
    subprocess.run([str(ROOT / 'root/usr/bin/tesseract'), '--version'], env=env, check=True)
    print('Local OCR installed:', ROOT)

if __name__ == '__main__':
    main()
