"""Gera pacotes reproduzíveis sem copiar banco, backups, segredos ou caches."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, hashlib, os, sys
ROOT=Path(__file__).resolve().parent
DIST=ROOT/'dist'
EXCLUDE={'__pycache__','.venv','.git','dist','.pytest_cache','backups'}
SUFFIXES={'.pyc','.db','.sqlite','.sqlite3','.log','.pem','.key'}
EXTRA={'.dsi_access_token','.env'}

def eligible(file):
    rel=file.relative_to(ROOT)
    return file.is_file() and not any(x in EXCLUDE for x in rel.parts) and file.name not in EXTRA and file.suffix not in SUFFIXES

def pack(target,files,base):
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for f in sorted(files):
            z.write(f,f.relative_to(base).as_posix())
    with ZipFile(target) as z:
        assert z.testzip() is None
        assert not any('.dsi_access_token' in n or n.endswith('dsi.db') for n in z.namelist())
    return hashlib.sha256(target.read_bytes()).hexdigest(),target.stat().st_size

def main():
    DIST.mkdir(exist_ok=True)
    project=DIST/'DSI_v1.0.0_projeto_local.zip'
    ext=DIST/'DSI_v1.0.0_firefox_nao_assinado.zip'
    src=[f for f in ROOT.rglob('*') if eligible(f)]
    hashes={}
    hashes[project.name]=pack(project,src,ROOT.parent)
    hashes[ext.name]=pack(ext,[f for f in (ROOT/'extension').rglob('*') if eligible(f)],ROOT/'extension')
    for name,(sha,size) in hashes.items():print(name,size,sha)
    print('Extensão NÃO ASSINADA: precisa de assinatura pelo Firefox Add-ons.')
if __name__=='__main__':main()
