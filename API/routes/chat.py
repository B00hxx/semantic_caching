from fastapi import APIRouter, Request
from API.schemas.query_request import QueryRequest

router = APIRouter(prefix='/chat', tags =["chat"])

@router.post('/fake_ask')
async def fake_ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.fake_testing.get_answers(query=query_request.query)
    return result


@router.post('/ttl_cache')
async def ask_ttl_cache(query_request : QueryRequest, request : Request):
    result = await request.app.state.ttl_cache.get_answers(query=query_request.query)
    return result

@router.post('/inactivity_cache')
async def ask_inactivity_cache(query_request : QueryRequest, request : Request):
    result = await request.app.state.inactivity_cache.get_answers(query=query_request.query)
    return result

@router.post('/hit_count_cache')
async def ask_hit_count_cache(query_request : QueryRequest, request : Request):
    result = await request.app.state.hit_count_cache.get_answers(query=query_request.query)
    return result

@router.post('/fifo_eviction_cache')
async def ask_fifo_eviction_cache(query_request : QueryRequest, request : Request):
    result = await request.app.state.fifo_eviction_cache.get_answers(query=query_request.query)
    return result

@router.post('/lfu_eviction_cache')
async def ask_lfu_eviction_cache(query_request : QueryRequest, request : Request):
    result = await request.app.state.lfu_eviction_cache.get_answers(query=query_request.query)
    return result

@router.post('/lru_eviction_cache')
async def ask_lru_eviction_cache(query_request : QueryRequest, request : Request):
    result = await request.app.state.lru_eviction_cache.get_answers(query=query_request.query)
    return result