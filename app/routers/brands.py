import json
import uuid
from fastapi import APIRouter, HTTPException
from app.db import connect, now
from app.schemas import BrandKit

router = APIRouter(prefix="/api/v1/brands", tags=["brand kits"])


@router.post("", status_code=201)
def create_brand(body: BrandKit):
    brand_id, timestamp = str(uuid.uuid4()), now()
    with connect() as db:
        db.execute("INSERT INTO brands(id,name,config_json,created_at,updated_at) VALUES(?,?,?,?,?)",
                   (brand_id, body.name, json.dumps(body.model_dump()), timestamp, timestamp))
    return {"id": brand_id, **body.model_dump(), "created_at": timestamp, "updated_at": timestamp}


@router.get("")
def list_brands():
    with connect() as db:
        rows = db.execute("SELECT * FROM brands ORDER BY created_at DESC").fetchall()
    return [{"id": r["id"], **json.loads(r["config_json"]), "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]


@router.get("/{brand_id}")
def get_brand(brand_id: str):
    with connect() as db:
        row = db.execute("SELECT * FROM brands WHERE id=?", (brand_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Brand kit not found")
    return {"id": row["id"], **json.loads(row["config_json"]), "created_at": row["created_at"], "updated_at": row["updated_at"]}


@router.put("/{brand_id}")
def update_brand(brand_id: str, body: BrandKit):
    timestamp = now()
    with connect() as db:
        changed = db.execute("UPDATE brands SET name=?,config_json=?,updated_at=? WHERE id=?",
                             (body.name, json.dumps(body.model_dump()), timestamp, brand_id)).rowcount
    if not changed:
        raise HTTPException(404, "Brand kit not found")
    return {"id": brand_id, **body.model_dump(), "updated_at": timestamp}
