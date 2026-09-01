import pytest
from config import settings
from semantic_caching.postgres_service.postgres_service import PostgresService

@pytest.fixture
def fake_components():
    return {
        "postgres_instance" : settings.postgres_service.get_service
    }

@pytest.mark.asyncio
async def test_postgres():
    pass
