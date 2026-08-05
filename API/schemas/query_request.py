from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query : str = Field(..., description="User query for the semantic caching project", example="What is semantic caching?")