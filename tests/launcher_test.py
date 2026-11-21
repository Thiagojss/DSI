"""Testes isolados do inicializador, sem iniciar API e sem tocar no SQLite."""
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dsi_launcher', root / 'launcher.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

with patch.object(launcher, 'server_health', return_value={'service': 'dsi-api', 'status': 'ok', 'version': '1.0.0'}), patch.object(launcher, 'webbrowser') as browser:
    assert launcher.start() == 0
    browser.open.assert_called_once_with('http://127.0.0.1:8000/dashboard')
with patch.object(launcher, 'server_health', return_value=None), patch.object(launcher, 'port_busy', return_value=True), patch.object(launcher, 'subprocess') as sub:
    assert launcher.start() == 2
    sub.Popen.assert_not_called()
with patch.object(launcher, 'server_health', return_value=None), patch.object(launcher, 'port_busy', return_value=False), patch.object(launcher, 'dependencies_missing', return_value=['fastapi']), patch.object(launcher, 'subprocess') as sub:
    assert launcher.start() == 2
    sub.Popen.assert_not_called()
with patch.object(launcher, 'dependencies_missing', return_value=[]), patch.object(launcher, 'server_health', return_value=None), patch.object(launcher, 'port_busy', return_value=False):
    with redirect_stdout(io.StringIO()) as out:
        assert launcher.diagnostic()
    assert 'Porta 8000: livre' in out.getvalue()
assert launcher.main(['--check']) in (0, 1)
print('OK: iniciante, conflito de porta, dependências e diagnóstico.')
