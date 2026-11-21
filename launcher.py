"""Iniciador local do DSI. Apenas stdlib; não modifica o banco nem instala silenciosamente."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
HOST = '127.0.0.1'
PORT = 8000
BASE_URL = f'http://{HOST}:{PORT}'
REQUIRED = ('fastapi', 'uvicorn', 'sqlalchemy', 'pydantic')


def dependencies_missing():
    return [name for name in REQUIRED if importlib.util.find_spec(name) is None]


def server_health(timeout=1):
    try:
        with urllib.request.urlopen(BASE_URL + '/health', timeout=timeout) as response:
            result = json.load(response)
        return result if result.get('service') == 'dsi-api' and result.get('status') == 'ok' else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def port_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, PORT)) == 0


def diagnostic():
    print('DSI — Diagnóstico local')
    print('Python:', sys.version.split()[0], '(necessário 3.10+)')
    valid_python = sys.version_info >= (3, 10)
    missing = dependencies_missing()
    print('Dependências:', 'OK' if not missing else ', '.join(missing) + ' ausente(s)')
    print('Pasta de dados:', ROOT / 'data')
    db = ROOT / 'data' / 'dsi.db'
    print('Banco:', 'existente — será preservado' if db.exists() else 'não criado — será criado no primeiro início')
    health = server_health()
    print('API:', f"conectada (v{health.get('version', '?')})" if health else 'não responde como DSI')
    print('Porta 8000:', 'em uso' if port_busy() else 'livre')
    if not valid_python: print('AÇÃO: instale Python 3.10 ou mais recente.')
    if missing: print('AÇÃO: use Instalar e iniciar DSI.bat ou execute python launcher.py --install.')
    if not health and port_busy(): print('AÇÃO: outra aplicação pode estar usando a porta 8000. Encerre-a antes de iniciar o DSI.')
    return valid_python and not missing and (bool(health) or not port_busy())


def install():
    print('Instalando dependências do projeto no ambiente Python atual...')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], cwd=ROOT)


def start(open_browser=True):
    existing = server_health()
    if existing:
        print('O servidor DSI já está ativo. Abrindo o painel existente.')
        if open_browser: webbrowser.open(BASE_URL + '/dashboard')
        return 0
    if port_busy():
        print('ERRO: a porta 8000 está ocupada por outro serviço. Não vou encerrá-lo nem substituir processos.')
        return 2
    if dependencies_missing():
        print('ERRO: dependências ausentes. Execute python launcher.py --install ou use Instalar e iniciar DSI.bat.')
        return 2
    env = os.environ.copy()
    command = [sys.executable, '-m', 'uvicorn', 'main:app', '--app-dir', str(ROOT / 'backend'), '--host', HOST, '--port', str(PORT)]
    print('Iniciando DSI apenas em', BASE_URL)
    server = subprocess.Popen(command, cwd=ROOT, env=env)
    try:
        for _ in range(60):
            if server.poll() is not None:
                print('ERRO: o servidor encerrou durante a inicialização. Veja a mensagem acima.')
                return 1
            if server_health(timeout=.35):
                print('DSI conectado. Para encerrar, feche esta janela ou pressione Ctrl+C.')
                if open_browser: webbrowser.open(BASE_URL + '/dashboard')
                return server.wait()
            time.sleep(.25)
        print('ERRO: tempo limite de inicialização. Verifique mensagens do servidor.')
        return 1
    except KeyboardInterrupt:
        print('\nEncerrando servidor local...')
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try: server.wait(timeout=5)
            except subprocess.TimeoutExpired: server.kill(); server.wait()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Inicia e diagnostica o DSI local.')
    parser.add_argument('--check', action='store_true', help='Mostra diagnóstico sem iniciar o servidor')
    parser.add_argument('--install', action='store_true', help='Instala dependências somente quando solicitado')
    parser.add_argument('--no-browser', action='store_true', help='Não abre o painel automaticamente')
    args = parser.parse_args(argv)
    if args.check: return 0 if diagnostic() else 1
    if sys.version_info < (3, 10):
        print('Python 3.10+ é necessário.'); return 2
    if args.install:
        try: install()
        except (OSError, subprocess.CalledProcessError) as exc:
            print('ERRO durante instalação:', exc); return 2
    return start(not args.no_browser)


if __name__ == '__main__':
    sys.exit(main())
