import httpx
from typing import Any, Dict


class CacheClient:

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str
    ):
        self.client = client
        self.base_url = base_url


    async def clear_cache(self) -> Dict[str, Any]:
        try:
            response = await self.client.delete(
                f"{self.base_url}/delete/fake_cache"
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "error": None
                }

            return {
                "success": False,
                "error": response.text
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }