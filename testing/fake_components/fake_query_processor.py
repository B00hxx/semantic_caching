from semantic_caching.query import RedactionResult


class FakeQueryProcessor:
    """Stands in for the Presidio client: no HTTP, scripted detections."""

    def __init__(self, entities: list[dict] | None = None, redacted_text: str | None = None):
        self.entities = entities or []
        self.redacted_text = redacted_text
        self.calls = 0

    async def process(self, query: str) -> RedactionResult:
        self.calls += 1
        text = self.redacted_text if self.redacted_text is not None else query
        return RedactionResult(text=text, entities=list(self.entities))
