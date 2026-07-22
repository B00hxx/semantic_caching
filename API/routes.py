from fastapi import APIRouter, Request
from ..config import settings


router = APIRouter()


@router.post('/ask')
async def ask_question(query : str, request : Request):
    result = request.app.state.semantic_caching_service.get_answers(query=query)
    if not result["cache_hit"]:
        return result
    else:
        result["ttl"] = request.app.state.semantic_caching_service.vector_store.ttl(result["id"])
        return result