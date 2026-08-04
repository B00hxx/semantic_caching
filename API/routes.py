import os
import httpx
import yaml
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from API.schemas.query_request import QueryRequest, DeleteQuery
from config import settings

router = APIRouter()

CUSTOM_RECOGNIZERS_DIR = "/app/custom-rules"
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://presidio-analyzer:5001/analyze")

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

@router.post('/delte_cache')
async def delete_cache(del_query : DeleteQuery, request : Request):
    if del_query.state:
        await request.app.state.semantic_caching_service.vector_store.empty_database()

@router.post('/fake_ask')
async def fake_ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.fake_testing.get_answers(query=query_request.query)
    return result


@router.post("/upload-redaction-rules/")
async def upload_redaction_rules(file: UploadFile = File(...)):
    if not (file.filename.endswith(".yaml") or file.filename.endswith(".yml")):
        raise HTTPException(status_code=400, detail="Only YAML files are allowed.")

    rules_dir = settings.presidio.custom_rules_dir
    os.makedirs(rules_dir, exist_ok=True)
    content = await file.read()
    try:
        parsed = yaml.safe_load(content)
        if not isinstance(parsed, dict) or "recognizers" not in parsed:
            raise ValueError("YAML file must contain a top-level 'recognizers' key.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML structure: {e}")

    file_path = os.path.join(rules_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(content)

    return {"status": "uploaded", "filename": file.filename}