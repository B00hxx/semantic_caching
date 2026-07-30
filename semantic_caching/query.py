import asyncio
import httpx

class Query:
    """This class can be used to redact the info that is sensitive"""
    def __init__(self, query : str):
        self.query = query
    async def process(self)->str:
        ANALYZER_URL = "http://localhost:5002/analyze"
        ANONYMIZER_URL = "http://localhost:5001/anonymize"
        async with httpx.AsyncClient(timeout=5.0) as client:
            analyze_payload = {
                "text": self.query,
                "language": "en",
            }
            analyze_response = await client.post(
                ANALYZER_URL,
                json=analyze_payload,
                headers={"Content-Type": "application/json"},
            )
            analyze_results = analyze_response.json()
            anonymize_payload = {
                        "text": self.query,
                        "anonymizers": {
                            "PHONE_NUMBER": {
                                "type": "replace",
                                "new_value": "--Redacted phone number--",
                            }
                        },
                        "analyzer_results": analyze_results,  # Feeding analyzer results directly
                    }
            
            anonymize_response = await client.post(
                        ANONYMIZER_URL,
                        json=anonymize_payload,
                        headers={"Content-Type": "application/json"},
                    )
            anonymize_results = anonymize_response.json()
        return anonymize_results['text']


test_query = Query("my phone number is +1221523470")
print(asyncio.run(test_query.process()))