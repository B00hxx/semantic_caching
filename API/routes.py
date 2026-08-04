import logging
import os
import re
import secrets
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from API.schemas.query_request import QueryRequest, DeleteQuery
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]+$")
MAX_RULES_FILE_BYTES = 256 * 1024


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Guard for endpoints that destroy cache data or write files to disk."""
    expected = settings.admin_token
    if not expected:
        logger.warning("ADMIN_TOKEN is not set: administrative endpoints are unprotected")
        return
    if x_admin_token is None or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token.")


@router.post('/ask')
async def ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.semantic_caching_service.get_answers(query=query_request.query)
    return result

@router.get('/stats')
async def get_stats(request : Request):
    info = await request.app.state.redis_client.info()
    return {
        "Total keys" : await request.app.state.semantic_caching_service.vector_store.get_size(),
        "Memory used (bytes)" : info['used_memory']
    }

@router.post('/delte_cache', dependencies=[Depends(require_admin)])
async def delete_cache(del_query : DeleteQuery, request : Request):
    if not del_query.state:
        return {"deleted": 0}
    deleted = await request.app.state.semantic_caching_service.vector_store.empty_database()
    deleted += await request.app.state.fake_testing.vector_store.empty_database()
    return {"deleted": deleted}

@router.post('/fake_ask')
async def fake_ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.fake_testing.get_answers(query=query_request.query)
    return result


@router.post("/upload-redaction-rules/", dependencies=[Depends(require_admin)])
async def upload_redaction_rules(file: UploadFile = File(...)):
    # Only ever trust the basename: the raw upload name may contain path separators
    # and the rules directory is a bind mount onto the host.
    filename = os.path.basename(file.filename or "")
    if not SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    if not filename.endswith((".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="Only YAML files are allowed.")

    rules_dir = settings.presidio.custom_rules_dir
    os.makedirs(rules_dir, exist_ok=True)
    content = await file.read()
    if len(content) > MAX_RULES_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Rules file is too large.")
    try:
        parsed = yaml.safe_load(content)
        if not isinstance(parsed, dict) or "recognizers" not in parsed:
            raise ValueError("YAML file must contain a top-level 'recognizers' key.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML structure: {e}")

    rules_root = Path(rules_dir).resolve()
    file_path = (rules_root / filename).resolve()
    if file_path.parent != rules_root:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path.write_bytes(content)

    # Recognizers are built when the analyzer process starts, so a new file only
    # takes effect after that container is restarted.
    return {
        "status": "uploaded",
        "filename": filename,
        "active": False,
        "detail": "Restart the presidio-analyzer service to load this file.",
    }