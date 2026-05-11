"""
eval/tune_semantic_threshold.py — Empirically tune the semantic cache threshold.

Computes cosine similarities for three categories of query pairs:
  - Same intent (should hit):  semantically equivalent phrasings of the same question
  - Near misses (should miss): similar-sounding but meaningfully different questions
  - Cross-module (must miss):  different Cerner modules (already isolated by key scheme)

Usage:
  python eval/tune_semantic_threshold.py

Output: prints similarity matrix and suggests threshold range.
The default SEMANTIC_CACHE_THRESHOLD=0.85 is empirically derived from this script.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Query pair definitions ─────────────────────────────────────────────────────

# Pairs expected to be cache hits (sim should be > threshold)
SHOULD_HIT = [
    (
        "How do I configure a dot phrase in PowerChart?",
        "What's the process for setting up auto-text abbreviations in PowerChart?",
        "POWERCHART",
    ),
    (
        "BCMA is showing an override prompt that won't clear",
        "BCMA override alert is stuck and I can't get past it",
        "CLINICAL",
    ),
    (
        "How do I look up a FHIR R4 Patient resource?",
        "What's the endpoint for querying Patient resources in FHIR R4?",
        "FHIR",
    ),
    (
        "Guarantor field is locked in registration",
        "I can't edit the guarantor in the patient registration screen",
        "REVENUE_CYCLE",
    ),
    (
        "How do I run a CCL report in Millennium?",
        "What are the steps to execute a CCL script in Cerner Millennium?",
        "MILLENNIUM",
    ),
]

# Pairs expected to be cache misses (sim should be < threshold)
SHOULD_MISS = [
    (
        "How do I configure a dot phrase in PowerChart?",
        "How do I add a new order set in PowerChart?",
        "POWERCHART",
    ),
    (
        "BCMA is showing an override prompt that won't clear",
        "eMAR timestamp is showing the wrong time zone",
        "CLINICAL",
    ),
    (
        "How do I look up a FHIR R4 Patient resource?",
        "How do I use FHIR R4 Observation resources for vitals?",
        "FHIR",
    ),
    (
        "Guarantor field is locked in registration",
        "ERA reconciliation is failing in Revenue Cycle",
        "REVENUE_CYCLE",
    ),
]


def cosine_sim(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def embed_batch(texts: list[str]):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]


def run():
    print("Loading BAAI/bge-large-en-v1.5 model...")
    all_texts = []
    for q1, q2, _ in SHOULD_HIT + SHOULD_MISS:
        all_texts.extend([q1, q2])

    vecs = embed_batch(all_texts)

    hit_sims = []
    miss_sims = []

    print("\n" + "=" * 70)
    print("SHOULD-HIT pairs (expected sim > threshold)")
    print("=" * 70)
    for i, (q1, q2, module) in enumerate(SHOULD_HIT):
        v1 = vecs[i * 2]
        v2 = vecs[i * 2 + 1]
        sim = cosine_sim(v1, v2)
        hit_sims.append(sim)
        flag = "OK" if sim > 0.85 else "LOW"
        print(f"  [{flag}] sim={sim:.4f}  module={module}")
        print(f"         Q1: {q1[:65]}")
        print(f"         Q2: {q2[:65]}")

    offset = len(SHOULD_HIT) * 2
    print("\n" + "=" * 70)
    print("SHOULD-MISS pairs (expected sim < threshold)")
    print("=" * 70)
    for i, (q1, q2, module) in enumerate(SHOULD_MISS):
        v1 = vecs[offset + i * 2]
        v2 = vecs[offset + i * 2 + 1]
        sim = cosine_sim(v1, v2)
        miss_sims.append(sim)
        flag = "OK" if sim < 0.85 else "HIGH"
        print(f"  [{flag}] sim={sim:.4f}  module={module}")
        print(f"         Q1: {q1[:65]}")
        print(f"         Q2: {q2[:65]}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    min_hit = min(hit_sims) if hit_sims else 0
    max_miss = max(miss_sims) if miss_sims else 0
    print(f"  Should-hit   min sim: {min_hit:.4f}")
    print(f"  Should-miss  max sim: {max_miss:.4f}")
    print(f"  Safe threshold range: ({max_miss:.3f}, {min_hit:.3f})")
    print(f"  Current SEMANTIC_CACHE_THRESHOLD: 0.85")

    if max_miss < 0.85 < min_hit:
        print("  [PASS] Default threshold 0.85 is within the safe range.")
    else:
        midpoint = (max_miss + min_hit) / 2
        print(f"  [ADJUST] Suggested threshold: {midpoint:.3f}")


if __name__ == "__main__":
    run()
