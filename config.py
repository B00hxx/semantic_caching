import redis.asyncio as redis
import ollama
import os
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from semantic_caching.postgres_service.postgres_service import PostgresService

class PostgresSettings(BaseModel):
    host: str = Field(
        default_factory=lambda: os.getenv("CACHE_POSTGRES_HOST", "postgres")
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_POSTGRES_PORT", "5432"))
    )
    database: str = Field(
        default_factory=lambda: os.getenv("CACHE_POSTGRES_DB")
    )
    user: str = Field(
        default_factory=lambda: os.getenv("CACHE_POSTGRES_USER")
    )
    password: str = Field(
        default_factory=lambda: os.getenv("CACHE_POSTGRES_PASSWORD")
    )

    async def get_service(self) -> PostgresService:
        postgres_service = PostgresService(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )

        await postgres_service.initialize()
        return postgres_service

class RedisSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    port: int = Field(
        default_factory=lambda: int(
            os.getenv('REDIS_PORT', 6380 if os.getenv('REDIS_HOST', 'localhost') in ('localhost', '127.0.0.1') else 6379)
        )
    )
    db: int = 0
    decode_responses: bool = False

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

class PresidioSettings(BaseModel):
    analyzer_url: str = Field(default_factory=lambda: os.getenv('ANALYZER_URL', 'http://localhost:5002/analyze'))
    anonymizer_url: str = Field(default_factory=lambda: os.getenv('ANONYMIZER_URL', 'http://localhost:5001/anonymize'))
    custom_rules_dir: str = Field(default_factory=lambda: os.getenv('CUSTOM_RULES_DIR', './custom_recognizers'))
    url_analyzer: str = "http://presidio-analyzer:3000"

class LiteLLMSettings(BaseModel):
    model_name : str = Field(default_factory=lambda: os.getenv('MODEL_NAME'))
    api_key : str = Field(default_factory=lambda: os.getenv('API_KEY'))
    embedding_model_name :str  = Field(default_factory=lambda: os.getenv('EMBEDDING_MODEL_NAME'))
    embedding_model_key : str = Field(default_factory=lambda: os.getenv('API_KEY_EMB'))
    embedding_model_dimension : int = Field(default_factory=lambda: os.getenv('EMBEDDING_MODEL_DIMENSION'))
    
class Settings(BaseSettings):
    cache_ttl_seconds : int = 3600
    cache_inactivity_seconds : int = 3600
    cache_min_hit_count : int = 2
    
    cache_invalidation_interval: int = 3600
    lite_llm_settings : LiteLLMSettings = Field(default_factory=LiteLLMSettings)
    redis_client: RedisSettings = Field(default_factory=RedisSettings)
    ollama_client: OllamaSettings = Field(default_factory=OllamaSettings)
    presidio: PresidioSettings = Field(default_factory=PresidioSettings)
    postgres_service : PostgresSettings = Field(default_factory=PostgresSettings)
    delete_on_shutdown: bool = False
    cache_eviction_interval: int = 1800
    cache_max_size: int = 100
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter='__',
        extra="ignore",
    )
    jwt_secret_key: str
    admin_username: str
    admin_password_hash: str
    admin_password : str

settings = Settings()