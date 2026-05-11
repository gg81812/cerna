"""
download_fhir.py — Download Cerner FHIR R4 reference docs into data/provider/.

Run once to populate the knowledge base with FHIR API documentation:
    python download_fhir.py

Files are saved as Markdown to data/provider/ so ingest.py picks them up
automatically under the 'provider' vertical.
"""

import requests
import os

DEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "provider")

BASE = "https://raw.githubusercontent.com/cerner/fhir.cerner.com/main/content/millennium"

FHIR_URLS = [
    # Overview
    f"{BASE}/r4.md",
    # Individuals
    f"{BASE}/r4/base/individuals/patient.md",
    f"{BASE}/r4/base/individuals/practitioner.md",
    f"{BASE}/r4/base/individuals/related-person.md",
    # Entities / Management
    f"{BASE}/r4/base/entities/organization.md",
    f"{BASE}/r4/base/entities/location.md",
    f"{BASE}/r4/base/management/encounter.md",
    # Workflow / Scheduling
    f"{BASE}/r4/base/workflow/appointment.md",
    f"{BASE}/r4/base/workflow/schedule.md",
    # Clinical — Diagnostics
    f"{BASE}/r4/clinical/diagnostics/observation.md",
    f"{BASE}/r4/clinical/diagnostics/diagnostic-report.md",
    # Clinical — Summary
    f"{BASE}/r4/clinical/summary/condition.md",
    f"{BASE}/r4/clinical/summary/allergy-intolerance.md",
    f"{BASE}/r4/clinical/summary/procedure.md",
    # Clinical — Medications
    f"{BASE}/r4/clinical/medications/medication-request.md",
    f"{BASE}/r4/clinical/medications/immunization.md",
    # Clinical — Care Provision
    f"{BASE}/r4/clinical/care-provision/care-plan.md",
    f"{BASE}/r4/clinical/care-provision/service-request.md",
    # Financial (payer-relevant)
    f"{BASE}/r4/financial/support/coverage.md",
    f"{BASE}/r4/financial/general/account.md",
]

os.makedirs(DEST_DIR, exist_ok=True)

print(f"Downloading FHIR docs -> {DEST_DIR}\n")
ok, fail = 0, 0

for url in FHIR_URLS:
    # Give files descriptive names: "fhir-r4-patient.md", "fhir-r4-encounter.md", etc.
    stem = url.split("/")[-1].replace(".md", "")          # e.g. "patient"
    # Top-level r4.md → "fhir-r4-overview.md"
    if stem == "r4":
        filename = "fhir-r4-overview.md"
    else:
        filename = f"fhir-r4-{stem}.md"

    dest_path = os.path.join(DEST_DIR, filename)

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"  OK  {filename}  ({len(r.text):,} chars)")
        ok += 1
    except requests.HTTPError as exc:
        print(f"  FAIL  {filename}  -- HTTP {exc.response.status_code}: {url}")
        fail += 1
    except Exception as exc:
        print(f"  FAIL  {filename}  -- {exc}")
        fail += 1

print(f"\nDone: {ok} downloaded, {fail} failed.")
if ok:
    print("\nNext step — rebuild the vector store:\n    python ingest.py")
