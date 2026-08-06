import httpx
from config import settings


async def reload_presidio_analyzer():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.presidio.url_analyzer}/reload"
        )

        response.raise_for_status() 