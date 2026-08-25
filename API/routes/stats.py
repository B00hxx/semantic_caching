from fastapi import APIRouter, Depends, Request
from API.auth.security import User, get_current_admin

router = APIRouter(prefix='/stats', tags=['stats'])

@router.get('/stats')
async def get_stats(request : Request, current_user: User = Depends(get_current_admin)):
    info = await request.app.state.redis_client.info()
    return {
        "Total keys" : await request.app.state.lite_testing.vector_store.get_size(),
        "Memory used (bytes)" : info['used_memory']
    }