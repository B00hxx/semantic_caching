from fastapi import APIRouter, Request
from API.schemas.query_request import DeleteQuery


router = APIRouter(prefix='/delete', tags =["delete"])


@router.post('/delte_cache')
async def delete_cache(del_query : DeleteQuery, request : Request):
    if del_query.state:
        await request.app.state.semantic_caching_service.vector_store.empty_database()
