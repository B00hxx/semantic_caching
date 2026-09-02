import asyncio

from fastapi import APIRouter, Depends, Request

from API.auth.security import User, get_current_admin
from API.schemas.query_request import NumberOfEntries


router = APIRouter(prefix="/stats", tags=["stats"])


@router.post("/postgres_entries")
async def get_postgres_stats(
    number_of_entries: NumberOfEntries,
    request: Request,
    current_user: User = Depends(get_current_admin),
):
    namespaces = [
        "ttl",
        "inactivity",
        "hit_count",
        "fifo_eviction",
        "lfu_eviction",
        "lru_eviction",
    ]

    postgres_service = request.app.state.postgres_service

    results = await asyncio.gather(
        *[
            postgres_service.get_top_entries(
                embedding_model="qwen-embedding",
                embedding_dimension=1024,
                namespace=namespace,
                limit=number_of_entries.k,
            )
            for namespace in namespaces
        ]
    )

    entries = []

    for namespace, namespace_entries in zip(namespaces, results):
        entries.extend(
            {
                "question": entry.question,
                "hit_count": entry.hit_count,
                "embedding_dimension": entry.embedding_dimension,
                "namespace": namespace,
            }
            for entry in namespace_entries
        )

    return {
        "count": len(entries),
        "entries": entries,
    }