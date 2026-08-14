from fastapi import APIRouter, Depends, Request

from API.auth.security import User, get_current_admin


router = APIRouter(prefix="/delete",tags=["delete"])

@router.delete("/cache")
async def delete_cache(request: Request,current_user: User = Depends(get_current_admin)):
    await request.app.state.lite_testing.vector_store.empty_database()
    return {
        "message": "Cache deleted successfully."
    }

@router.delete("/fake_cache")
async def delete_cache(request: Request,current_user: User = Depends(get_current_admin)):
    await request.app.state.fake_testing.vector_store.empty_database()
    return {
        "message": "Fake Cache deleted successfully."
    }