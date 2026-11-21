from pathlib import Path
from fastapi.responses import FileResponse

DASHBOARD_FILE = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

def dashboard_page():
    return FileResponse(DASHBOARD_FILE)
