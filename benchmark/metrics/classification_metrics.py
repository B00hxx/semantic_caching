class ClassificationMetrics():
    def __init__(self):
        self.true_positives = 0
        self.false_positives = 0
        self.true_negatives = 0
        self.false_negatives = 0
    
    def update(self, cache_hit: bool, is_duplicate: int) -> None:
        if cache_hit and is_duplicate == 1:
            self.true_positives += 1

        elif cache_hit and is_duplicate == 0:
            self.false_positives += 1

        elif not cache_hit and is_duplicate == 1:
            self.false_negatives += 1

        else:
            self.true_negatives += 1
    def accuracy(self):
        total = (
            self.true_positives
            + self.false_positives
            + self.true_negatives
            + self.false_negatives
        )

        if total == 0:
            return 0

        return (self.true_positives + self.true_negatives) / total


    def precision(self):
        denominator = (
            self.true_positives
            + self.false_positives
        )

        if denominator == 0:
            return 0

        return self.true_positives / denominator


    def recall(self):
        denominator = (
            self.true_positives
            + self.false_negatives
        )

        if denominator == 0:
            return 0

        return self.true_positives / denominator


    def f1_score(self):
        precision = self.precision()
        recall = self.recall()

        if precision + recall == 0:
            return 0

        return (
            2 * precision * recall
        ) / (precision + recall)


    def results(self):
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "accuracy": self.accuracy(),
            "precision": self.precision(),
            "recall": self.recall(),
            "f1_score": self.f1_score(),
        }