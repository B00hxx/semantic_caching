import logging
import os
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.pattern import Pattern
from presidio_analyzer.pattern_recognizer import PatternRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("presidio-analyzer")


CUSTOM_RULES_DIR = os.getenv(
    "CUSTOM_RULES_DIR",
    "/app/custom-rules",
)


# -----------------------------------------------------------------------------
# Custom recognizer loading
# -----------------------------------------------------------------------------

def load_custom_recognizers(registry: RecognizerRegistry) -> None:
    """
    Load custom Presidio PatternRecognizers from YAML files.

    Expected YAML structure:

    recognizers:
      - name: MyRecognizer
        supported_language: en
        supported_entity: MY_ENTITY
        patterns:
          - name: my_pattern
            regex: "\\b...\\b"
            score: 0.8
        deny_list:
          - example
    """

    if not os.path.isdir(CUSTOM_RULES_DIR):
        logger.info(
            "No custom rules directory found at %s",
            CUSTOM_RULES_DIR,
        )
        return

    for filename in sorted(os.listdir(CUSTOM_RULES_DIR)):
        if not filename.endswith((".yaml", ".yml")):
            continue

        path = os.path.join(CUSTOM_RULES_DIR, filename)

        logger.info("Loading custom recognizers from %s", path)

        try:
            with open(path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            if not config or not isinstance(config, dict):
                logger.warning(
                    "Skipping %s: YAML root is not a dictionary",
                    filename,
                )
                continue

            recognizers = config.get("recognizers", [])

            if not isinstance(recognizers, list):
                logger.warning(
                    "Skipping %s: 'recognizers' must be a list",
                    filename,
                )
                continue

            for recognizer_config in recognizers:
                if not isinstance(recognizer_config, dict):
                    logger.warning(
                        "Skipping invalid recognizer in %s",
                        filename,
                    )
                    continue

                name = recognizer_config.get("name")
                entity = recognizer_config.get("supported_entity")
                language = recognizer_config.get(
                    "supported_language",
                    "en",
                )

                if not name:
                    logger.warning(
                        "Skipping recognizer without a name in %s",
                        filename,
                    )
                    continue

                if not entity:
                    logger.warning(
                        "Skipping recognizer '%s': "
                        "missing supported_entity",
                        name,
                    )
                    continue

                patterns = []

                for pattern_config in recognizer_config.get(
                    "patterns",
                    [],
                ):
                    if not isinstance(pattern_config, dict):
                        continue

                    pattern_name = pattern_config.get("name")
                    regex = pattern_config.get("regex")
                    score = pattern_config.get("score")

                    if not pattern_name or not regex or score is None:
                        logger.warning(
                            "Skipping invalid pattern in recognizer '%s'",
                            name,
                        )
                        continue

                    patterns.append(
                        Pattern(
                            name=pattern_name,
                            regex=regex,
                            score=float(score),
                        )
                    )

                if not patterns and not recognizer_config.get("deny_list"):
                    logger.warning(
                        "Skipping recognizer '%s': "
                        "no patterns or deny_list",
                        name,
                    )
                    continue

                recognizer_kwargs: dict[str, Any] = {
                    "name": name,
                    "supported_entity": entity,
                    "supported_language": language,
                    "patterns": patterns,
                }

                deny_list = recognizer_config.get("deny_list")

                if deny_list:
                    recognizer_kwargs["deny_list"] = deny_list

                recognizer = PatternRecognizer(
                    **recognizer_kwargs
                )

                registry.add_recognizer(recognizer)

                logger.info(
                    "Successfully registered custom recognizer: "
                    "%s (%s)",
                    name,
                    entity,
                )

        except Exception:
            logger.exception(
                "Error loading custom recognizer file %s",
                filename,
            )


# -----------------------------------------------------------------------------
# Presidio initialization
# -----------------------------------------------------------------------------

def create_analyzer() -> AnalyzerEngine:
    """
    Create and configure the Presidio AnalyzerEngine.
    """

    registry = RecognizerRegistry()

    # Load Presidio's built-in recognizers.
    registry.load_predefined_recognizers()

    # Load our own YAML-defined recognizers.
    load_custom_recognizers(registry)

    analyzer = AnalyzerEngine(
        registry=registry,
    )

    return analyzer


analyzer = create_analyzer()


# -----------------------------------------------------------------------------
# FastAPI application
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Custom Presidio Analyzer",
    version="1.0.0",
)


# -----------------------------------------------------------------------------
# Request / response models
# -----------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    text: str
    language: str = "en"
    entities: list[str] | None = None
    score_threshold: float = 0.0


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    """
    Health check endpoint.
    """

    return {
        "status": "ok",
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> list[dict[str, Any]]:
    """
    Analyze text for PII / sensitive entities.
    """

    if not request.text:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty.",
        )

    try:
        results = analyzer.analyze(
            text=request.text,
            language=request.language,
            entities=request.entities,
            score_threshold=request.score_threshold,
        )

        return [
            {
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
                "recognition_metadata": result.recognition_metadata,
            }
            for result in results
        ]

    except Exception as exc:
        logger.exception("Error while analyzing text")

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# -----------------------------------------------------------------------------
# Local execution
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
    )