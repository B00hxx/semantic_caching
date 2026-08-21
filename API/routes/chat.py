from fastapi import APIRouter, Request
from API.schemas.query_request import QueryRequest

router = APIRouter(prefix='/chat', tags =["chat"])

@router.post('/fake_ask')
async def fake_ask_question(query_request : QueryRequest, request : Request):
    result = await request.app.state.fake_testing.get_answers(query=query_request.query)
    return result


@router.post('/ttl_cache')
async def ask_lite_llm(query_request : QueryRequest, request : Request):
    result = await request.app.state.ttl_cache.get_answers(query=query_request.query)
    return result