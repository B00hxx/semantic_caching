from fastapi import APIRouter, Depends, Request
from API.auth.security import User, get_current_admin

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/get_all_entries")
async def get_all_entries(request: Request, current_user: User = Depends(get_current_admin)):
    entries = await request.app.state.ttl_cache.vector_store.get_all_entries()

    return {
        "count": len(entries),
        "entries": [
            {
                "id": str(entry.id),
                "question": entry.question,
                "answer": entry.answer,
                "namespace": entry.namespace,
                "created_at": entry.created_at.isoformat(),
                "ttl_seconds": entry.ttl_seconds,
                "hit_count": entry.hit_count,
                "last_hit_at": (
                    entry.last_hit_at.isoformat()
                    if entry.last_hit_at
                    else None
                ),
                "last_accessed_at": (
                    entry.last_accessed_at.isoformat()
                    if entry.last_accessed_at
                    else None
                ),
                "embedding_dimension": len(entry.embedding),
            }
            for entry in entries
        ],
    }