import asyncio

from fastapi import APIRouter, Depends, Request

from API.auth.security import User, get_current_admin


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/get_all_entries")
async def get_all_entries(
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    caches = {
        "ttl": request.app.state.ttl_cache,
        "inactivity": request.app.state.inactivity_cache,
        "hit_count": request.app.state.hit_count_cache,
        "fifo_eviction": request.app.state.fifo_eviction_cache,
        "lfu_eviction": request.app.state.lfu_eviction_cache,
        "lru_eviction": request.app.state.lru_eviction_cache,
    }

    results = await asyncio.gather(
        *[
            cache.vector_store.get_all_entries()
            for cache in caches.values()
        ]
    )

    entries = []

    for namespace, namespace_entries in zip(caches.keys(), results):
        entries.extend(
            {
                "id": str(entry.id),
                "question": entry.question,
                "answer": entry.answer,
                "namespace": namespace,
                "created_at": entry.created_at.isoformat(),
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
            for entry in namespace_entries
        )

    return {
        "count": len(entries),
        "entries": entries,
    }
