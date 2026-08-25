from fastapi import APIRouter, Depends, Request
from API.auth.security import User, get_current_admin
from API.schemas.query_request import NumberOfEntries

router = APIRouter(prefix='/stats', tags=['stats'])

@router.post('/postgres_entries')
async def get_postgres_stats(number_of_entries : NumberOfEntries, request: Request, current_user: User = Depends(get_current_admin)):
    entries = await request.app.state.postgres_service.get_top_entries(
        embedding_model="qwen-embedding",
        embedding_dimension=1024,
        namespace="default",
        limit=number_of_entries.k,
    )

    return {
        "entries": [
            {
                "question": entry.question,
                "hit_count": entry.hit_count,
                "embedding_dimension" : entry.embedding_dimension
            }
            for entry in entries
        ]
    }