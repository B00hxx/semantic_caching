from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query : str = Field(..., description="User query for the semantic caching project", example="What is semantic caching?")

class DeleteQuery(BaseModel):
    state : bool = Field(False, description="this is used to delete the cache db when set to true")