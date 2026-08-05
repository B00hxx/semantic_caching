from fastapi import APIRouter, Request

router = APIRouter(prefix="/delete", tags=["delete"])


@router.delete("/cache")
async def delete_cache(request: Request):
    await request.app.state.semantic_caching_service.vector_store.empty_database()

    return {"message": "Cache deleted successfully."}