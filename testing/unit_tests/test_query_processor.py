import pytest
from semantic_caching.query import QueryProcessor, SENSITIVE_ENTITIES


def test_contains_sensitive_data():
    processor = QueryProcessor()

    sensitive_spans = [
        {"entity_type": "PERSON", "start": 0, "end": 8, "score": 0.95}
    ]
    assert processor.contains_sensitive_data(sensitive_spans) is True

    custom_sensitive_spans = [
        {"entity_type": "EMPLOYEE_ID", "start": 5, "end": 14, "score": 0.9}
    ]
    assert processor.contains_sensitive_data(custom_sensitive_spans) is True

    non_sensitive_spans = [
        {"entity_type": "DATE_TIME", "start": 0, "end": 4, "score": 0.8}
    ]
    assert processor.contains_sensitive_data(non_sensitive_spans) is False


def test_redact_query():
    processor = QueryProcessor()
    text = "My name is John Doe and my email is john@example.com."
    spans = [
        {"entity_type": "PERSON", "start": 11, "end": 19, "score": 0.95},
        {"entity_type": "EMAIL_ADDRESS", "start": 36, "end": 52, "score": 0.99},
    ]

    redacted = processor.redact(query=text, analyzer_results=spans)
    assert redacted == "My name is <REDACTED> and my email is <REDACTED>."
