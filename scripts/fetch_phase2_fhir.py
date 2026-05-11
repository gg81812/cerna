"""
scripts/fetch_phase2_fhir.py — One-shot fetcher for the Phase 2 FHIR additions.

Downloads R4 resource markdown files from cerner/fhir.cerner.com that are
present in the upstream repo but missing from data/fhir/. Each file is saved
with the project's standard 5-line header (SOURCE / URL / MODULE / RETRIEVED).

Usage:
    python scripts/fetch_phase2_fhir.py
"""

import os
import sys
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_DIR

DEST = os.path.join(DATA_DIR, "fhir")
TODAY = date.today().isoformat()
BASE = "https://raw.githubusercontent.com/cerner/fhir.cerner.com/main/content/millennium"

# (output_filename, upstream_path, human_title)
TARGETS = [
    ("fhir-service-request.md",
     "/r4/clinical/care-provision/service-request.md",
     "FHIR R4 ServiceRequest Resource — Cerner Implementation"),
    ("fhir-schedule.md",
     "/r4/base/workflow/schedule.md",
     "FHIR R4 Schedule Resource — Cerner Implementation"),
    ("fhir-person-resource.md",
     "/r4/base/individuals/person.md",
     "FHIR R4 Person Resource — Cerner Implementation"),
    ("fhir-device-resource.md",
     "/r4/base/entities/device.md",
     "FHIR R4 Device Resource — Cerner Implementation"),
    ("fhir-account-resource.md",
     "/r4/financial/general/account.md",
     "FHIR R4 Account Resource — Cerner Implementation"),
    ("fhir-charge-item.md",
     "/r4/financial/general/charge-item.md",
     "FHIR R4 ChargeItem Resource — Cerner Implementation"),
    ("fhir-financial-transaction.md",
     "/r4/financial/general/financial-transaction.md",
     "FHIR R4 FinancialTransaction Resource — Cerner Implementation"),
    ("fhir-insurance-plan.md",
     "/r4/financial/general/insurance-plan.md",
     "FHIR R4 InsurancePlan Resource — Cerner Implementation"),
    ("fhir-questionnaire-response.md",
     "/r4/clinical/diagnostics/questionnaire-response.md",
     "FHIR R4 QuestionnaireResponse Resource — Cerner Implementation"),
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "cerna-phase2/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> None:
    os.makedirs(DEST, exist_ok=True)
    ok = 0
    fail = 0
    too_short = 0
    for fname, path, title in TARGETS:
        url = BASE + path
        out = os.path.join(DEST, fname)
        try:
            body = fetch(url).strip()
        except Exception as exc:
            print(f"  FAIL  {fname}  -- {exc}")
            fail += 1
            continue

        word_count = len(body.split())
        if word_count < 300:
            print(f"  WARN  {fname}  -- only {word_count} words; below 300-word minimum")
            too_short += 1
            # Still write so we can review; will exclude before ingest if still too short.

        header = (
            f"# SOURCE: {title}\n"
            f"# URL: {url}\n"
            f"# MODULE: FHIR & Integrations\n"
            f"# RETRIEVED: {TODAY}\n"
            f"# ---\n\n"
        )
        with open(out, "w", encoding="utf-8") as f:
            f.write(header + body + "\n")
        print(f"  OK    {fname}  ({word_count:,} words, {len(body):,} chars)")
        ok += 1

    print()
    print(f"  {ok} written, {fail} failed, {too_short} below 300 words")


if __name__ == "__main__":
    main()
