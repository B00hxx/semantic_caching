import os
from fastapi import APIRouter, Request
from API.schemas.query_request import QueryRequest, DeleteQuery


router = APIRouter()


@router.post('/ask')
async def ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.semantic_caching_service.get_answers(query=query_request.query)
    return result

@router.get('/stats')
async def get_stats(request : Request):
    info = await request.app.state.redis_client.info()
    return {
        "Total keys" : await request.app.state.semantic_caching_service.vector_store.get_size(),
        "Memory used (bytes)" : info['used_memory']
    }

@router.post('/delte_cache')
async def delete_cache(del_query : DeleteQuery, request : Request):
    if del_query.state:
        await request.app.state.semantic_caching_service.vector_store.empty_database()

@router.post('/fake_ask')
async def fake_ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.fake_testing.get_answers(query=query_request.query)
    return result