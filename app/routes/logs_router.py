import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.dependecies import current_superuser
from app.models.models import User

logs_router = APIRouter(prefix="/logs", tags=["logs"])

HERE = os.path.abspath(os.path.dirname(__file__))           # .../app/routes
APP_DIR = os.path.abspath(os.path.join(HERE, ".."))         # .../app
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, "..")) # ...
DEFAULT_LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

LOGS_DIR = os.path.abspath(os.getenv("LOGS_DIR", DEFAULT_LOGS_DIR))
ALLOWED_EXT = {".log", ".txt"}

def _ensure_logs_dir_exists():
    if not os.path.isdir(LOGS_DIR):
        raise HTTPException(status_code=404, detail=f"logs dir not found: {LOGS_DIR}")

def _safe_join_logs(filename: str) -> str:
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="invalid filename")
    base, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="unsupported extension")
    full = os.path.abspath(os.path.join(LOGS_DIR, filename))
    root = os.path.abspath(LOGS_DIR)
    if not (full == root or full.startswith(root + os.sep)):
        raise HTTPException(status_code=400, detail="outside logs dir")
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="file not found")
    return full

def _tail_lines(path: str, limit: int) -> List[str]:
    # эффективный tail последних N строк
    try:
        fsize = os.path.getsize(path)
    except OSError:
        return []
    block = 8192
    data = bytearray()
    with open(path, "rb") as f:
        pos = fsize
        while pos > 0 and data.count(b"\n") <= limit:
            read = block if pos - block > 0 else pos
            pos -= read
            f.seek(pos)
            data[:0] = f.read(read)
    return [l.decode(errors="replace") for l in data.splitlines()[-limit:]]

@logs_router.get("/files", response_model=List[str])
async def list_log_files(
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_logs_dir_exists()
    files = []
    for name in os.listdir(LOGS_DIR):
        full = os.path.join(LOGS_DIR, name)
        if os.path.isfile(full) and os.path.splitext(name)[1].lower() in ALLOWED_EXT:
            files.append(name)
    weight = {"error": 0, "app": 1, "db": 2, "access": 3}
    files.sort(key=lambda n: (weight.get(os.path.splitext(n)[0], 9), n.lower()))
    return files

@logs_router.get("", response_model=dict)
async def get_log_tail(
    file: str = Query(..., description="имя файла, напр. app.log"),
    limit: int = Query(1000, ge=1, le=5000),
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_logs_dir_exists()
    path = _safe_join_logs(file)
    lines = _tail_lines(path, limit)
    return {"file": file, "lines": lines, "dir": LOGS_DIR}

@logs_router.get("/download")
async def download_log(
    file: str = Query(...),
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_logs_dir_exists()
    path = _safe_join_logs(file)

    def stream():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        stream(),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'},
    )
