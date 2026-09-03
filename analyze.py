import re
import statistics
from collections import defaultdict

pattern = re.compile(
    r"Endpoint=http://[^/]+/chat/([^ ]+) "
    r"\| query=\d+/\d+ \| status=(\d+) "
    r"\| hit=(True|False) \| latency=([\d.]+)s"
)

data = defaultdict(lambda: {"hits": [], "misses": []})

with open("workers_test.txt", encoding="utf-8") as file:
    for line in file:
        match = pattern.search(line)
        if not match:
            continue

        policy, status, hit, latency = match.groups()

        if status != "200":
            continue

        latency = float(latency)

        if hit == "True":
            data[policy]["hits"].append(latency)
        else:
            data[policy]["misses"].append(latency)


def p95(values):
    if len(values) < 2:
        return values[0] if values else 0
    return statistics.quantiles(values, n=100, method="inclusive")[94]


for policy, groups in data.items():
    hits = groups["hits"]
    misses = groups["misses"]
    all_requests = hits + misses

    if not all_requests:
        continue

    hit_mean = statistics.mean(hits) if hits else 0
    miss_mean = statistics.mean(misses) if misses else 0

    print(f"\n{policy}")
    print("-" * len(policy))
    print(f"Requests:       {len(all_requests)}")
    print(f"Hits:           {len(hits)}")
    print(f"Misses:         {len(misses)}")
    print(f"Hit rate:       {len(hits) / len(all_requests):.2%}")

    print(f"Hit mean:       {hit_mean:.3f}s")
    print(f"Hit median:     {statistics.median(hits):.3f}s" if hits else "Hit median:     n/a")
    print(f"Hit p95:        {p95(hits):.3f}s" if hits else "Hit p95:        n/a")

    print(f"Miss mean:      {miss_mean:.3f}s")
    print(f"Miss median:    {statistics.median(misses):.3f}s" if misses else "Miss median:    n/a")
    print(f"Miss p95:       {p95(misses):.3f}s" if misses else "Miss p95:       n/a")

    if hits and misses:
        print(f"Mean speedup:    {miss_mean / hit_mean:.1f}x")
        print(f"Mean time saved: {miss_mean - hit_mean:.3f}s per hit")