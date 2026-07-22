import os
from fastapi import APIRouter, Request
from .schemas.query_request import QueryRequest


router = APIRouter()


@router.post('/ask')
def ask_question(query_request : QueryRequest, request : Request):
    result = request.app.state.semantic_caching_service.get_answers(query=query_request.query)
    return result