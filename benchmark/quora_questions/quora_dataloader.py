import pandas as pd
from .question_pair import QuoraQuestionsPair

class QuoraDataLoader():
    def __init__(self, path : str = "benchmark/datasets/train.csv") -> list[QuoraQuestionsPair]:
        self.path = path
    def load(self, limit: int | None = None):
        dataframe = pd.read_csv(self.path)
        if limit:
            dataframe = dataframe.head(limit)
        pairs = []
        for _, row in dataframe.iterrows():
            pairs.append(
                QuoraQuestionsPair(
                    question1=row["question1"],
                    question2=row["question2"],
                    is_duplicate=int(row["is_duplicate"])
                )
            )
        return pairs
        