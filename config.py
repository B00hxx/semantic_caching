import redis.asyncio as redis
import ollama
import os
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    port: int = Field(default_factory=lambda: int(os.getenv('REDIS_PORT', 6379)))
    db: int = 0
    decode_responses: bool = True

    def get_client(self) -> redis.Redis:
        return redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=self.decode_responses
        )


class OllamaSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv('OLLAMA_HOST', 'http://localhost:11434'))

    def get_client(self) -> ollama.AsyncClient:
        return ollama.AsyncClient(
            host=self.host
        )

class Settings(BaseSettings):
    redis_client: RedisSettings = Field(default_factory=RedisSettings)
    ollama_client: OllamaSettings = Field(default_factory=OllamaSettings)
    delete_on_shutdown: bool = True
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter='__'
    )

settings = Settings()