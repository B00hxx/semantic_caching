import json
import matplotlib.pyplot as plt


with open("visualizations/results.json", "r") as file:
    results = json.load(file)


# Convert JSON dictionary into ordered data
results = {
    float(threshold): metrics
    for threshold, metrics in results.items()
}

thresholds = sorted(results.keys())


# ============================================================
# 1. PERFORMANCE METRICS
# ============================================================

accuracy = [
    results[t]["accuracy"] * 100
    for t in thresholds
]

precision = [
    results[t]["precision"] * 100
    for t in thresholds
]

recall = [
    results[t]["recall"] * 100
    for t in thresholds
]

f1 = [
    results[t]["f1_score"] * 100
    for t in thresholds
]


plt.figure(figsize=(10, 6))

plt.plot(
    thresholds,
    accuracy,
    marker="o",
    label="Accuracy"
)

plt.plot(
    thresholds,
    precision,
    marker="o",
    label="Precision"
)

plt.plot(
    thresholds,
    recall,
    marker="o",
    label="Recall"
)

plt.plot(
    thresholds,
    f1,
    marker="o",
    label="F1 Score"
)

plt.xlabel("Similarity Threshold")
plt.ylabel("Score (%)")
plt.title("Semantic Cache Performance vs Similarity Threshold")

plt.xticks(thresholds)
plt.ylim(0, 100)

plt.grid(True, alpha=0.3)
plt.legend()

plt.tight_layout()
plt.savefig(
    "performance_vs_threshold.png",
    dpi=300
)

plt.show()


# ============================================================
# 2. CONFUSION MATRIX COMPONENTS
# ============================================================

tp = [
    results[t]["true_positives"]
    for t in thresholds
]

fp = [
    results[t]["false_positives"]
    for t in thresholds
]

tn = [
    results[t]["true_negatives"]
    for t in thresholds
]

fn = [
    results[t]["false_negatives"]
    for t in thresholds
]


plt.figure(figsize=(10, 6))

plt.plot(
    thresholds,
    tp,
    marker="o",
    label="True Positives"
)

plt.plot(
    thresholds,
    fp,
    marker="o",
    label="False Positives"
)

plt.plot(
    thresholds,
    tn,
    marker="o",
    label="True Negatives"
)

plt.plot(
    thresholds,
    fn,
    marker="o",
    label="False Negatives"
)

plt.xlabel("Similarity Threshold")
plt.ylabel("Number of Samples")
plt.title("Confusion Matrix Components vs Similarity Threshold")

plt.xticks(thresholds)

plt.grid(True, alpha=0.3)
plt.legend()

plt.tight_layout()
plt.savefig(
    "confusion_matrix_vs_threshold.png",
    dpi=300
)

plt.show()


# ============================================================
# 3. PRECISION-RECALL TRADEOFF
# ============================================================

plt.figure(figsize=(8, 6))

plt.plot(
    recall,
    precision,
    marker="o"
)

for i, threshold in enumerate(thresholds):
    plt.annotate(
        f"{threshold:.2f}",
        (recall[i], precision[i]),
        xytext=(6, 6),
        textcoords="offset points"
    )

plt.xlabel("Recall (%)")
plt.ylabel("Precision (%)")
plt.title("Precision–Recall Tradeoff")

plt.xlim(0, 100)
plt.ylim(0, 100)

plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(
    "precision_recall_tradeoff.png",
    dpi=300
)


plt.figure(figsize=(9, 5))

plt.plot(
    thresholds,
    f1,
    marker="o"
)

best_index = f1.index(max(f1))
best_threshold = thresholds[best_index]
best_f1 = f1[best_index]

plt.scatter(
    best_threshold,
    best_f1,
    s=100,
    zorder=5
)

plt.annotate(
    f"Best: {best_threshold:.2f} ({best_f1:.2f}%)",
    (best_threshold, best_f1),
    xytext=(10, 10),
    textcoords="offset points"
)

plt.xlabel("Similarity Threshold")
plt.ylabel("F1 Score (%)")
plt.title("F1 Score vs Similarity Threshold")

plt.xticks(thresholds)
plt.ylim(0, 100)

plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(
    "f1_vs_threshold.png",
    dpi=300
)

plt.show()