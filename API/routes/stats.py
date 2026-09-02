from fastapi import APIRouter, Depends, Request
from API.auth.security import User, get_current_admin

router = APIRouter(prefix='/stats', tags=['stats'])

@router.get('/stats')
async def get_stats(request : Request, current_user: User = Depends(get_current_admin)):
    info = await request.app.state.redis_client.info()
    return {
        "ttl_cache_stats" : await request.app.state.ttl_cache.vector_store.get_size(),
        "inactivity_cache_stats" : await request.app.state.inactivity_cache.vector_store.get_size(),
        "hit_count_cache_stats" : await request.app.state.hit_count_cache.vector_store.get_size(),
        "fifo_eviction_cache_stats" : await request.app.state.fifo_eviction_cache.vector_store.get_size(),
        "lfu_eviction_cache_stats" : await request.app.state.lfu_eviction_cache.vector_store.get_size(),
        "lru_eviction_cache_stats" : await request.app.state.lru_eviction_cache.vector_store.get_size(),
        "Memory used (bytes)" : info['used_memory']
    }