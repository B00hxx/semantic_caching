import httpx


class AuthClient:

    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self.client = client
        self.base_url = base_url


    async def login(self, username: str, password: str) -> str:
        response = await self.client.post(
            f"{self.base_url}/auth/login",
            data={
                "username": username,
                "password": password
            }
        )

        response.raise_for_status()

        return response.json()["access_token"]