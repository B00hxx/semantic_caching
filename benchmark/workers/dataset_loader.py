from pathlib import Path
import pandas as pd


def load_lmsys_queries(
    dataset_directory: str,
    max_queries: int | None = None,
) -> list[str]:

    dataset_path = Path(dataset_directory)

    parquet_files = sorted(
        dataset_path.glob("*.parquet")
    )

    if not parquet_files:
        raise FileNotFoundError(
            f"No parquet files found in {dataset_directory}"
        )

    print(f"Found {len(parquet_files)} parquet files.")

    queries = []

    for parquet_file in parquet_files:

        print(f"Loading {parquet_file.name}...")

        df = pd.read_parquet(parquet_file)

        if "conversation" not in df.columns:
            print(
                f"Skipping {parquet_file.name}: "
                "'conversation' column not found."
            )
            continue

        for conversation in df["conversation"]:

            if conversation is None or len(conversation) == 0:
                continue

            for message in conversation:

                if not isinstance(message, dict):
                    continue

                if message.get("role") != "user":
                    continue

                content = message.get("content")

                if content is None:
                    continue

                content = str(content).strip()

                if not content:
                    continue

                queries.append(content)

                if (
                    max_queries is not None
                    and len(queries) >= max_queries
                ):
                    print(
                        f"Reached max_queries={max_queries}"
                    )
                    return queries

    print(f"Loaded {len(queries)} user queries.")

    return queries