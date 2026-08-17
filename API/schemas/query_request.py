from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query : str = Field(..., description="User query for the semantic caching project", example="What is semantic caching?")

class NumberOfEntries(BaseModel):
    k : int = Field(..., description="The number of entries to fetch from postgres", example=10)