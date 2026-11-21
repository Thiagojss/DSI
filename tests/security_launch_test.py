"""Testes isolados de segurança v1.0. Não altera dados da instalação do usuário."""
import os, sys, tempfile
from pathlib import Path
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory(prefix='dsi-v1-security-') as tmp:
    os.environ['DSI_DATABASE_PATH'] = str(Path(tmp) / 'isolated.db')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    import main
    client = TestClient(main.app)
    token = main.LOCAL_ACCESS_TOKEN
    assert (Path(tmp) / '.dsi_access_token').exists()
    assert len(token) == 64
    assert main.load_access_token() == token
    assert client.get('/health').status_code == 200
    preflight = client.options('/products', headers={
        'Origin': 'moz-extension://a1b2c3-d4e5',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'x-dsi-token,content-type',
    })
    assert preflight.status_code == 200, preflight.text
    assert 'x-dsi-token' in preflight.headers.get('access-control-allow-headers','').lower()
    assert client.options('/products', headers={
        'Origin': 'https://evil.example',
        'Access-Control-Request-Method': 'POST',
    }).status_code == 403
    assert client.get('/products').status_code == 401
    assert client.post('/products', json={'title': 'Teste', 'url': 'https://www.aliexpress.com/item/1005001234567890.html'}).status_code == 401
    assert client.get('/settings/export-products.csv').status_code == 401
    assert client.get('/products', headers={'X-DSI-Token': '0'*64}).status_code == 401
    h = {'X-DSI-Token': token}
    assert client.get('/products', headers=h).status_code == 200
    assert client.get('/settings/export-products.csv', headers=h).status_code == 200
    assert client.get('/products', headers={**h,'Origin':'https://external.example'}).status_code == 403
    assert client.post('/settings/backup', json={'confirmation':'CRIAR BACKUP'}, headers={**h,'Origin':'https://external.example'}).status_code == 403
    assert client.get('/products', headers={**h,'Host':'external.example'}).status_code == 400
    page = client.get('/dashboard')
    assert page.status_code == 200 and token in page.text
    assert page.headers['cache-control'] == 'no-store'
    assert page.headers['x-frame-options'] == 'DENY'
    assert page.headers['content-security-policy'] == "frame-ancestors 'none'"
    assert client.get('/openapi.json').status_code == 401
    assert client.post('/settings/backup', headers=h, json={'confirmation':'CRIAR BACKUP'}).status_code == 200
print('OK: persistência da chave, acesso protegido, origem, Host, CSV, dashboard e backup.')
