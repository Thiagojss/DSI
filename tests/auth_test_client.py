"""Cliente de testes com autenticação real em banco temporário."""
from fastapi.testclient import TestClient as RealTestClient
class TestClient(RealTestClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from main import LOCAL_ACCESS_TOKEN
        self.headers.update({"X-DSI-Token": LOCAL_ACCESS_TOKEN})
