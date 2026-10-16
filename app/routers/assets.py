import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.config import settings
from app.db import connect, now
from app.utils.files import safe_suffix

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])
CHUNK_SIZE = 1024 * 1024


@router.post("", status_code=201)
async def upload_asset(file: UploadFile = File(...)):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4())
    suffix = safe_suffix(file.filename)
    target = settings.upload_dir / f"{asset_id}{suffix}"
    size = 0
    try:
        with target.open("wb") as out:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_upload_mb * 1024 * 1024:
                    raise HTTPException(413, f"Upload exceeds {settings.max_upload_mb} MB limit")
                out.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    record = {"id": asset_id, "filename": file.filename or target.name, "content_type": file.content_type, "size_bytes": size, "created_at": now()}
    with connect() as db:
        db.execute("INSERT INTO assets(id,filename,stored_path,content_type,size_bytes,created_at) VALUES(?,?,?,?,?,?)",
                   (asset_id, record["filename"], str(target.resolve()), file.content_type, size, record["created_at"]))
    return record


@router.get("")
def list_assets():
    with connect() as db:
        return [dict(row) | {"stored_path": None} for row in db.execute("SELECT id,filename,stored_path,content_type,size_bytes,created_at FROM assets ORDER BY created_at DESC").fetchall()]


@router.get("/{asset_id}")
def get_asset(asset_id: str):
    with connect() as db:
        row = db.execute("SELECT id,filename,stored_path,content_type,size_bytes,created_at FROM assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Asset not found")
    return dict(row) | {"stored_path": None}
