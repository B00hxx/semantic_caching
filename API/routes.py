from fastapi import APIRouter
from ..config import settings
from .semantic_caching_service import testing

router = APIRouter()

@router.get("/status")
async def get_redis_status():
    return {
        "Redis Status" : settings.redis_client.get_client().ping()
    }


@router.post('/ask')
async def ask_question(query : str):
    return testing.get_answers(query=query)