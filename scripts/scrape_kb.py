"""
scripts/scrape_kb.py — Download all publicly accessible Cerner documentation
into the correct data/ subfolders.

Usage:
    python scripts/scrape_kb.py

Behaviour:
- Saves each file with a metadata header (SOURCE, URL, MODULE, RETRIEVED)
- Skips files that already exist (idempotent)
- Retries with a browser User-Agent on non-200 responses
- Waits 1 second between requests (rate limiting)
- Prints a final summary: X succeeded, Y failed, Z skipped
"""

import os
import sys
import time
from datetime import date
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

# ── Project root ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

TODAY = date.today().isoformat()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TIMEOUT = 10  # seconds


def make_header(title: str, url: str, module: str) -> str:
    return (
        f"# SOURCE: {title}\n"
        f"# URL: {url}\n"
        f"# MODULE: {module}\n"
        f"# RETRIEVED: {TODAY}\n"
        f"# ---\n\n"
    )


def download(url: str, dest_path: Path, title: str, module: str) -> str:
    """
    Download url to dest_path. Returns 'success', 'skipped', or 'failed'.
    """
    if dest_path.exists():
        return "skipped"

    # Attempt 1: plain GET
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"  [FAIL] {dest_path.name} — network error: {exc}")
        return "failed"

    # Attempt 2: retry with Accept: text/plain for raw GitHub content
    if resp.status_code != 200:
        retry_headers = dict(HEADERS)
        retry_headers["Accept"] = "text/plain"
        try:
            resp = requests.get(url, headers=retry_headers, timeout=TIMEOUT)
        except requests.RequestException as exc:
            print(f"  [FAIL] {dest_path.name} — retry network error: {exc}")
            return "failed"

    if resp.status_code != 200:
        print(f"  [FAIL] {dest_path.name} — HTTP {resp.status_code} from {url}")
        return "failed"

    content = make_header(title, url, module) + resp.text
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(content, encoding="utf-8")
    print(f"  [OK]   {dest_path.name}")
    return "success"


# ── Download manifest ─────────────────────────────────────────────────────────
# Each entry: (module_folder, filename, url, title, module_label)

GH_RAW = "https://raw.githubusercontent.com/cerner/fhir.cerner.com/main/content/millennium/r4"

MANIFEST = [
    # ── data/fhir/ — corrected GitHub paths (verified via GitHub API 2026-04-16)
    (
        "fhir", "fhir-r4-overview.md",
        f"{GH_RAW}.md",
        "Cerner FHIR R4 Overview",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-patient-resource.md",
        f"{GH_RAW}/base/individuals/patient.md",
        "FHIR R4 Patient Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-practitioner-resource.md",
        f"{GH_RAW}/base/individuals/practitioner.md",
        "FHIR R4 Practitioner Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-related-person.md",
        f"{GH_RAW}/base/individuals/related-person.md",
        "FHIR R4 RelatedPerson Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-encounter-resource.md",
        f"{GH_RAW}/base/management/encounter.md",
        "FHIR R4 Encounter Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-organization-resource.md",
        f"{GH_RAW}/base/entities/organization.md",
        "FHIR R4 Organization Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-location-resource.md",
        f"{GH_RAW}/base/entities/location.md",
        "FHIR R4 Location Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-appointment.md",
        f"{GH_RAW}/base/workflow/appointment.md",
        "FHIR R4 Appointment Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-slot-resource.md",
        f"{GH_RAW}/base/workflow/slot.md",
        "FHIR R4 Slot Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-allergy-intolerance.md",
        f"{GH_RAW}/clinical/summary/allergy-intolerance.md",
        "FHIR R4 AllergyIntolerance Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-condition-resource.md",
        f"{GH_RAW}/clinical/summary/condition.md",
        "FHIR R4 Condition Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-procedure-resource.md",
        f"{GH_RAW}/clinical/summary/procedure.md",
        "FHIR R4 Procedure Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-medication-request.md",
        f"{GH_RAW}/clinical/medications/medication-request.md",
        "FHIR R4 MedicationRequest Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-immunization-resource.md",
        f"{GH_RAW}/clinical/medications/immunization.md",
        "FHIR R4 Immunization Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-medication-administration.md",
        f"{GH_RAW}/clinical/medications/medication-administration.md",
        "FHIR R4 MedicationAdministration Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-observation-resource.md",
        f"{GH_RAW}/clinical/diagnostics/observation.md",
        "FHIR R4 Observation Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-diagnostic-report.md",
        f"{GH_RAW}/clinical/diagnostics/diagnostic-report.md",
        "FHIR R4 DiagnosticReport Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-care-plan.md",
        f"{GH_RAW}/clinical/care-provision/care-plan.md",
        "FHIR R4 CarePlan Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-goal-resource.md",
        f"{GH_RAW}/clinical/care-provision/goal.md",
        "FHIR R4 Goal Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-coverage-resource.md",
        f"{GH_RAW}/financial/support/coverage.md",
        "FHIR R4 Coverage Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-document-reference.md",
        f"{GH_RAW}/foundation/documents/document-reference.md",
        "FHIR R4 DocumentReference Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),
    (
        "fhir", "fhir-binary-resource.md",
        f"{GH_RAW}/foundation/other/binary.md",
        "FHIR R4 Binary Resource — Cerner Implementation",
        "FHIR & Integrations",
    ),

    # ── data/millennium/ ───────────────────────────────────────────────────────
    (
        "millennium", "millennium-mpages-explained.txt",
        "https://ehrenhancify.com/oracle-health-mpages/",
        "Oracle Health MPages — Overview and Development Guide",
        "Millennium Platform",
    ),
    (
        "millennium", "millennium-implementation-guide.txt",
        "https://www.ghit.digital/insight/detail/implementing-oracle-health-cerner-ehr",
        "Implementing Oracle Health Cerner EHR — Architecture and Build Guide",
        "Millennium Platform",
    ),
    (
        "millennium", "millennium-integration-pathways.txt",
        "https://www.tactionsoft.com/blog/cerner-oracle-health-integration-guide/",
        "Cerner Oracle Health Integration Guide — APIs and Architecture",
        "Millennium Platform",
    ),
    (
        "millennium", "millennium-developer-program.txt",
        "https://6b.health/insight/what-is-the-oracle-health-cerner-millennium-developer-program/",
        "Oracle Health Millennium Developer Program — Overview",
        "Millennium Platform",
    ),
    (
        "millennium", "millennium-ccl-open-source.txt",
        "https://engineering.cerner.com/post/",
        "Cerner Engineering Blog — CCL Unit, MPages and Architecture Posts",
        "Millennium Platform",
    ),

    # ── data/powerchart/ ───────────────────────────────────────────────────────
    (
        "powerchart", "powerchart-implementation-build.txt",
        "https://www.ghit.digital/insight/detail/implementing-oracle-health-cerner-ehr",
        "PowerChart Build Configuration — Powerforms, Powerplans, MPages",
        "PowerChart",
    ),
    (
        "powerchart", "powerchart-mpages-overview.txt",
        "https://ehrenhancify.com/oracle-health-mpages/",
        "MPages in PowerChart — Summary and Workflow Views",
        "PowerChart",
    ),
    (
        "powerchart", "powerchart-ai-integration-context.txt",
        "https://www.notev.ai/blog/cerner-integration-complete-guide-to-ai-scribe-oracle-health-connectivity-2025",
        "PowerChart Integration — Chart Architecture and Note Delivery",
        "PowerChart",
    ),

    # ── data/revenue_cycle/ ────────────────────────────────────────────────────
    (
        "revenue_cycle", "rcm-cerner-product-overview.txt",
        "https://www.cerner.com/en/solutions/revenue-cycle-management",
        "Cerner Revenue Cycle Management — Product Overview and CDRC Philosophy",
        "Revenue Cycle",
    ),
    (
        "revenue_cycle", "rcm-charge-capture-reconciliation.txt",
        "https://resources.cerecore.net/charge-capture-and-reconciliation-for-strong-revenue-cycle-management",
        "Charge Capture and Reconciliation — RCM Metrics and Workflow",
        "Revenue Cycle",
    ),
    (
        "revenue_cycle", "rcm-cdrc-concept-explained.txt",
        "https://www.techtarget.com/revcyclemanagement/answer/Cerners-Next-Step-With-Revenue-Cycle-Management-Technology",
        "Cerner Clinically Driven Revenue Cycle — Concept and Strategy",
        "Revenue Cycle",
    ),
    (
        "revenue_cycle", "rcm-medcare-workflow-guide.txt",
        "https://medcaremso.com/ehr-billing-service/cerner/",
        "Cerner RCM Workflows — RevElate, Charge Capture, CDI, HealtheAnalytics",
        "Revenue Cycle",
    ),
    (
        "revenue_cycle", "rcm-implementation-build-guide.txt",
        "https://www.ghit.digital/insight/detail/implementing-oracle-health-cerner-ehr",
        "Revenue Cycle Build Tasks — CDI, HIM, Interface Engine Configuration",
        "Revenue Cycle",
    ),

    # ── data/clinical/ ─────────────────────────────────────────────────────────
    (
        "clinical", "clinical-implementation-build-guide.txt",
        "https://www.ghit.digital/insight/detail/implementing-oracle-health-cerner-ehr",
        "Clinical Build Tasks — Powerforms, Powerplans, CareGuides, OFCt Testing",
        "Clinical Workflows",
    ),
    (
        "clinical", "clinical-ai-scribe-powerchart.txt",
        "https://www.notev.ai/blog/cerner-integration-complete-guide-to-ai-scribe-oracle-health-connectivity-2025",
        "Clinical Documentation Workflow — eMAR, CPOE, Note Generation in Cerner",
        "Clinical Workflows",
    ),
]


def main():
    print("=" * 65)
    print("Cerna Knowledge Base Scraper")
    print(f"Date: {TODAY}")
    print("=" * 65)

    succeeded = 0
    failed = 0
    skipped = 0
    failed_list = []

    for i, (folder, filename, url, title, module) in enumerate(MANIFEST):
        dest = DATA_DIR / folder / filename
        print(f"\n[{i+1}/{len(MANIFEST)}] {filename}")
        print(f"  URL: {url}")

        result = download(url, dest, title, module)

        if result == "success":
            succeeded += 1
        elif result == "skipped":
            skipped += 1
            print(f"  [SKIP] Already exists.")
        else:
            failed += 1
            failed_list.append((filename, url))

        if result != "skipped":
            time.sleep(1)

    print("\n" + "=" * 65)
    print("SCRAPE SUMMARY")
    print("=" * 65)
    print(f"  Succeeded : {succeeded}")
    print(f"  Failed    : {failed}")
    print(f"  Skipped   : {skipped}")
    print(f"  Total     : {len(MANIFEST)}")

    if failed_list:
        print("\nFailed downloads (manual intervention needed):")
        for name, u in failed_list:
            print(f"  - {name}")
            print(f"    {u}")

    print("\nNext step: python scripts/kb_status.py")


if __name__ == "__main__":
    main()
