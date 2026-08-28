import asyncio
import httpx


async def main():

    async with httpx.AsyncClient(
        timeout=None,
        trust_env=False,
    ) as client:

        print("BEFORE REQUEST", flush=True)

        response = await client.post(
            "http://127.0.0.1:8000/chat/ttl_cache",
            json={"query": "hello"},
        )

        print("AFTER REQUEST", flush=True)

        print("STATUS:", response.status_code)
        print("BODY:", response.text)


if __name__ == "__main__":
    asyncio.run(main())