"""Look at why new-25 queries failed on BGE: retrieval miss vs rate-limit."""
import json
from pathlib import Path

NEW_25_IDS = (
    [f"hs-it-{i:03d}" for i in range(9, 18)]
    + [f"hs-nurse-{i:03d}" for i in range(16, 23)]
    + [f"hs-physician-{i:03d}" for i in range(11, 15)]
    + [f"hs-clerk-{i:03d}" for i in range(13, 18)]
)

bge_path = Path(__file__).parent / "hospital_eval_v2_results_bge.jsonl"
mini_path = Path(__file__).parent / "hospital_eval_v2_results.jsonl"


def load(p: Path) -> dict[str, dict]:
    out = {}
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                out[r["id"]] = r
    return out


bge = load(bge_path)
mini = load(mini_path)

print(f"{'id':<22} {'BGE':<6} {'MiniLM':<6} {'BGE conf':<10} {'BGE chunk':<12} {'BGE behav':<12} {'BGE khr':<8}")
print("-" * 90)
for qid in NEW_25_IDS:
    b = bge.get(qid, {})
    m = mini.get(qid, {})
    b_pass = "PASS" if b.get("passed") else "FAIL"
    m_pass = "PASS" if m.get("passed") else "FAIL"
    print(
        f"{qid:<22} {b_pass:<6} {m_pass:<6} "
        f"{b.get('confidence','?'):<10} "
        f"top={b.get('top_chunk_score', 0):<8.3f} "
        f"{b.get('actual_behavior','?'):<12} "
        f"{b.get('keyword_hit_rate', 0):<8.0%}"
    )

print()
# Aggregate diagnostic
fail_no_chunk = sum(1 for qid in NEW_25_IDS
                    if not bge.get(qid, {}).get("passed")
                    and bge.get(qid, {}).get("top_chunk_score", 0) < 0.3)
fail_low_conf = sum(1 for qid in NEW_25_IDS
                    if not bge.get(qid, {}).get("passed")
                    and bge.get(qid, {}).get("confidence") == "low")
fail_error = sum(1 for qid in NEW_25_IDS
                 if not bge.get(qid, {}).get("passed")
                 and bge.get(qid, {}).get("confidence") == "error")
fail_clarify = sum(1 for qid in NEW_25_IDS
                   if not bge.get(qid, {}).get("passed")
                   and bge.get(qid, {}).get("actual_behavior") == "clarify")

print("New-25 failure mode summary on BGE:")
print(f"  Failed with very low chunk score (<0.3) : {fail_no_chunk}  -> retrieval miss / new content didn't surface")
print(f"  Failed with confidence=low              : {fail_low_conf}  -> retrieval below confidence threshold")
print(f"  Failed with confidence=error            : {fail_error}  -> hard error (likely rate-limit)")
print(f"  Failed with actual_behavior=clarify     : {fail_clarify} -> needs_clarify routing fired")

# Sample top chunk score distribution
print("\nNew-25 top_chunk_score distribution (BGE):")
scores = [bge.get(qid, {}).get("top_chunk_score", 0) for qid in NEW_25_IDS]
buckets = {"<0.30": 0, "0.30-0.45": 0, "0.45-0.60": 0, ">=0.60": 0}
for s in scores:
    if s < 0.30: buckets["<0.30"] += 1
    elif s < 0.45: buckets["0.30-0.45"] += 1
    elif s < 0.60: buckets["0.45-0.60"] += 1
    else: buckets[">=0.60"] += 1
for k, v in buckets.items():
    print(f"  {k:<12}: {v}")
