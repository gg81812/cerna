"""
scripts/fetch_phase2_module.py — Multi-source web fetcher for Phase 2 KB expansion.

Reads target URLs from per-module target lists below, fetches each, performs
basic HTML cleaning, enforces the 300-word minimum, and writes the result to
data/<module>/<filename> with the project's standard 5-line header.

Usage:
    python scripts/fetch_phase2_module.py <module>

Where <module> is one of: millennium, powerchart, revenue_cycle, clinical, cross_module.
"""

import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_DIR

try:
    from bs4 import BeautifulSoup
    _BS4 = True
except ImportError:
    _BS4 = False

TODAY = date.today().isoformat()
USER_AGENT = "Mozilla/5.0 (compatible; cerna-phase2/1.0)"

# Per-module target lists.
# (output_filename, url, human_title, friendly_module_label)
TARGETS = {
    "millennium": [
        ("millennium-ehrenhancify-overview.txt",
         "https://ehrenhancify.com/oracle-health-cerner-ehr/",
         "Oracle Health Cerner EHR — Platform Overview",
         "Millennium Platform"),
        ("millennium-ehrenhancify-modules.txt",
         "https://ehrenhancify.com/oracle-cerner-modules/",
         "Oracle Cerner Modules — Functional Breakdown",
         "Millennium Platform"),
        ("millennium-tactionsoft-deep-dive.txt",
         "https://www.tactionsoft.com/blog/cerner-millennium-deep-dive/",
         "Cerner Millennium Architecture Deep Dive",
         "Millennium Platform"),
        ("millennium-tactionsoft-implementation.txt",
         "https://www.tactionsoft.com/blog/cerner-implementation-best-practices/",
         "Cerner Implementation Best Practices",
         "Millennium Platform"),
        ("millennium-ghit-modernization.txt",
         "https://www.ghit.digital/insight/detail/oracle-health-modernization-strategy",
         "Oracle Health Modernization Strategy — GHIT Digital",
         "Millennium Platform"),
        ("millennium-ghit-data-migration.txt",
         "https://www.ghit.digital/insight/detail/cerner-data-migration",
         "Cerner Data Migration Patterns — GHIT Digital",
         "Millennium Platform"),
        ("millennium-6b-integration-strategies.txt",
         "https://6b.health/insight/cerner-integration-strategies/",
         "Cerner Integration Strategies — 6B.health",
         "Millennium Platform"),
        ("millennium-oracle-platform-apis.txt",
         "https://docs.oracle.com/en/industries/health/millennium-platform-apis/index.html",
         "Oracle Health Millennium Platform APIs — Index",
         "Millennium Platform"),
        ("millennium-oracle-developer-overview.txt",
         "https://docs.oracle.com/en/industries/health/millennium-developer/",
         "Oracle Health Millennium Developer Overview",
         "Millennium Platform"),
        ("millennium-oci-architecture.txt",
         "https://docs.oracle.com/en/industries/health/health-data-intelligence/",
         "Oracle Health Data Intelligence — Hosting Architecture",
         "Millennium Platform"),
        ("millennium-engineering-microservices.txt",
         "https://web.archive.org/web/2023/https://engineering.cerner.com/blog/microservices-the-easy-way-is-the-wrong-way/",
         "Cerner Engineering — Microservices Architecture Patterns",
         "Millennium Platform"),
        ("millennium-engineering-typescript-graphql.txt",
         "https://web.archive.org/web/2023/https://engineering.cerner.com/blog/rock-solid-components-with-typescript-and-graphql/",
         "Cerner Engineering — TypeScript and GraphQL Components",
         "Millennium Platform"),
        ("millennium-engineering-terra-accessibility.txt",
         "https://web.archive.org/web/2023/https://engineering.cerner.com/blog/lessons-learned-building-an-accessible-web-application-framework/",
         "Cerner Engineering — Terra Web Application Framework",
         "Millennium Platform"),
        ("millennium-cerner-wiki-overview.txt",
         "https://en.wikipedia.org/wiki/Oracle_Cerner",
         "Oracle Cerner — Wikipedia Overview",
         "Millennium Platform"),
        ("millennium-wiki-hl7.txt",
         "https://en.wikipedia.org/wiki/Health_Level_7",
         "Health Level 7 — Wikipedia",
         "Millennium Platform"),
        ("millennium-wiki-hie.txt",
         "https://en.wikipedia.org/wiki/Health_information_exchange",
         "Health Information Exchange — Wikipedia",
         "Millennium Platform"),
        ("millennium-wiki-mumps.txt",
         "https://en.wikipedia.org/wiki/MUMPS",
         "MUMPS Programming Language — Wikipedia (CCL ancestor context)",
         "Millennium Platform"),
        ("millennium-wiki-ldap.txt",
         "https://en.wikipedia.org/wiki/Lightweight_Directory_Access_Protocol",
         "LDAP — Wikipedia",
         "Millennium Platform"),
        ("millennium-wiki-soa.txt",
         "https://en.wikipedia.org/wiki/Service-oriented_architecture",
         "Service-Oriented Architecture — Wikipedia",
         "Millennium Platform"),
        ("millennium-wiki-ehr-interop.txt",
         "https://en.wikipedia.org/wiki/Interoperability",
         "Interoperability — Wikipedia",
         "Millennium Platform"),
        ("millennium-ahrq-ehr-adoption.txt",
         "https://psnet.ahrq.gov/primer/health-information-technology",
         "AHRQ PSNet — Health Information Technology",
         "Millennium Platform"),
    ],
    "powerchart": [
        ("powerchart-wiki-cpoe.txt",
         "https://en.wikipedia.org/wiki/Computerized_physician_order_entry",
         "Computerized Physician Order Entry — Wikipedia",
         "PowerChart"),
        ("powerchart-wiki-ehr.txt",
         "https://en.wikipedia.org/wiki/Electronic_health_record",
         "Electronic Health Record — Wikipedia",
         "PowerChart"),
        ("powerchart-wiki-cdss.txt",
         "https://en.wikipedia.org/wiki/Clinical_decision_support_system",
         "Clinical Decision Support System — Wikipedia",
         "PowerChart"),
        ("powerchart-wiki-emr-vs-ehr.txt",
         "https://en.wikipedia.org/wiki/Electronic_medical_record",
         "Electronic Medical Record — Wikipedia",
         "PowerChart"),
        ("powerchart-ahrq-cpoe-primer.txt",
         "https://psnet.ahrq.gov/primer/computerized-provider-order-entry",
         "AHRQ PSNet Primer — Computerized Provider Order Entry",
         "PowerChart"),
        ("powerchart-ahrq-medrec-primer.txt",
         "https://psnet.ahrq.gov/primer/medication-reconciliation",
         "AHRQ PSNet Primer — Medication Reconciliation",
         "PowerChart"),
        ("powerchart-ahrq-handoffs.txt",
         "https://psnet.ahrq.gov/primer/handoffs-and-signouts",
         "AHRQ PSNet Primer — Handoffs and Signouts",
         "PowerChart"),
        ("powerchart-ahrq-alert-fatigue.txt",
         "https://psnet.ahrq.gov/primer/alert-fatigue",
         "AHRQ PSNet Primer — Alert Fatigue",
         "PowerChart"),
        ("powerchart-ahrq-clinical-documentation.txt",
         "https://psnet.ahrq.gov/primer/clinical-documentation-improvement",
         "AHRQ PSNet Primer — Clinical Documentation",
         "PowerChart"),
        ("powerchart-wiki-eprescribing.txt",
         "https://en.wikipedia.org/wiki/Electronic_prescribing",
         "Electronic Prescribing — Wikipedia",
         "PowerChart"),
        ("powerchart-wiki-mpages.txt",
         "https://en.wikipedia.org/wiki/Cerner",
         "Cerner — Wikipedia (PowerChart and MPages context)",
         "PowerChart"),
        ("powerchart-wiki-clinical-pathway.txt",
         "https://en.wikipedia.org/wiki/Clinical_pathway",
         "Clinical Pathway — Wikipedia",
         "PowerChart"),
        ("powerchart-wiki-medical-software.txt",
         "https://en.wikipedia.org/wiki/Medical_software",
         "Medical Software — Wikipedia",
         "PowerChart"),
        ("powerchart-cms-promoting-interop.txt",
         "https://www.cms.gov/medicare/regulations-guidance/promoting-interoperability-programs",
         "CMS — Promoting Interoperability Programs",
         "PowerChart"),
        ("powerchart-onc-certification.txt",
         "https://www.healthit.gov/topic/certification-ehrs/about-onc-health-it-certification-program",
         "ONC Health IT Certification Program",
         "PowerChart"),
    ],
    "revenue_cycle": [
        ("rcm-hfma-clean-claim-rate.txt",
         "https://www.hfma.org/topics/revenue-cycle/clean-claim-rate/",
         "HFMA — Clean Claim Rate Benchmarks",
         "Revenue Cycle"),
        ("rcm-hfma-denial-management.txt",
         "https://www.hfma.org/topics/revenue-cycle/denial-management/",
         "HFMA — Denial Management Best Practices",
         "Revenue Cycle"),
        ("rcm-hfma-days-in-ar.txt",
         "https://www.hfma.org/topics/revenue-cycle/days-in-ar/",
         "HFMA — Days in Accounts Receivable Benchmarks",
         "Revenue Cycle"),
        ("rcm-hfma-revenue-cycle-kpis.txt",
         "https://www.hfma.org/topics/revenue-cycle/key-performance-indicators/",
         "HFMA — Revenue Cycle Key Performance Indicators",
         "Revenue Cycle"),
        ("rcm-cms-icd10-overview.txt",
         "https://www.cms.gov/medicare/coding-billing/icd-10-codes",
         "CMS — ICD-10 Coding Reference",
         "Revenue Cycle"),
        ("rcm-cms-medicare-billing.txt",
         "https://www.cms.gov/medicare/billing/medicare-billing-information",
         "CMS — Medicare Billing Information",
         "Revenue Cycle"),
        ("rcm-nucc-place-of-service.txt",
         "https://www.nucc.org/index.php/code-sets-mainmenu-41/place-of-service-codes-mainmenu-90",
         "NUCC — Place of Service Codes",
         "Revenue Cycle"),
        ("rcm-medcaremso-billing.txt",
         "https://medcaremso.com/cerner-billing-services/",
         "Cerner Billing Services — MedCare MSO",
         "Revenue Cycle"),
        ("rcm-medcaremso-charge-capture.txt",
         "https://medcaremso.com/cerner-charge-capture/",
         "Cerner Charge Capture Workflow — MedCare MSO",
         "Revenue Cycle"),
        ("rcm-medcaremso-denial-workflow.txt",
         "https://medcaremso.com/cerner-denial-management/",
         "Cerner Denial Management Workflow — MedCare MSO",
         "Revenue Cycle"),
        ("rcm-cerecore-revenue-cycle.txt",
         "https://cerecore.net/cerner-revenue-cycle/",
         "Cerner Revenue Cycle Optimization — CereCore",
         "Revenue Cycle"),
        ("rcm-cerecore-patient-access.txt",
         "https://cerecore.net/cerner-patient-access/",
         "Cerner Patient Access Workflow — CereCore",
         "Revenue Cycle"),
        ("rcm-revelate-overview.txt",
         "https://www.oracle.com/health/clinical-and-operations/revenue-cycle/",
         "Oracle Health Revelate Revenue Cycle — Product Overview",
         "Revenue Cycle"),
        ("rcm-ghit-revenue-cycle.txt",
         "https://www.ghit.digital/insight/detail/cerner-revenue-cycle",
         "Cerner Revenue Cycle Implementation — GHIT Digital",
         "Revenue Cycle"),
        ("rcm-ama-cpt-overview.txt",
         "https://www.ama-assn.org/practice-management/cpt/cpt-overview-and-code-approval",
         "AMA — CPT Overview and Code Approval Process",
         "Revenue Cycle"),
        ("rcm-wiki-icd10.txt",
         "https://en.wikipedia.org/wiki/ICD-10",
         "ICD-10 — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-icd10-cm.txt",
         "https://en.wikipedia.org/wiki/ICD-10-CM",
         "ICD-10-CM — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-cpt.txt",
         "https://en.wikipedia.org/wiki/Current_Procedural_Terminology",
         "Current Procedural Terminology — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-medical-billing.txt",
         "https://en.wikipedia.org/wiki/Medical_billing",
         "Medical Billing — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-x12-837.txt",
         "https://en.wikipedia.org/wiki/X12_Document_List",
         "X12 EDI Standards (837 claims) — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-revenue-cycle.txt",
         "https://en.wikipedia.org/wiki/Revenue_cycle_management",
         "Revenue Cycle Management — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-claim-denial.txt",
         "https://en.wikipedia.org/wiki/Health_insurance_in_the_United_States",
         "U.S. Health Insurance and Claim Adjudication — Wikipedia",
         "Revenue Cycle"),
        ("rcm-wiki-hipaa.txt",
         "https://en.wikipedia.org/wiki/Health_Insurance_Portability_and_Accountability_Act",
         "HIPAA — Wikipedia",
         "Revenue Cycle"),
    ],
    "clinical": [
        ("clinical-wiki-bcma.txt",
         "https://en.wikipedia.org/wiki/Bar_code_medication_administration",
         "Bar Code Medication Administration — Wikipedia",
         "Clinical Workflows"),
        ("clinical-wiki-emar.txt",
         "https://en.wikipedia.org/wiki/Medication_administration_record",
         "Medication Administration Record — Wikipedia",
         "Clinical Workflows"),
        ("clinical-wiki-medrec.txt",
         "https://en.wikipedia.org/wiki/Medication_reconciliation",
         "Medication Reconciliation — Wikipedia",
         "Clinical Workflows"),
        ("clinical-wiki-sepsis-treatment.txt",
         "https://en.wikipedia.org/wiki/Sepsis",
         "Sepsis — Wikipedia (clinical recognition and bundle)",
         "Clinical Workflows"),
        ("clinical-wiki-fall-prevention.txt",
         "https://en.wikipedia.org/wiki/Fall_prevention",
         "Fall Prevention — Wikipedia",
         "Clinical Workflows"),
        ("clinical-wiki-restraint-medical.txt",
         "https://en.wikipedia.org/wiki/Physical_restraint",
         "Physical Restraint — Wikipedia (medical use)",
         "Clinical Workflows"),
        ("clinical-wiki-pain-assessment.txt",
         "https://en.wikipedia.org/wiki/Pain_scale",
         "Pain Scale — Wikipedia",
         "Clinical Workflows"),
        ("clinical-wiki-clinical-decision-support.txt",
         "https://en.wikipedia.org/wiki/Patient_safety",
         "Patient Safety — Wikipedia",
         "Clinical Workflows"),
        ("clinical-ahrq-bcma-primer.txt",
         "https://psnet.ahrq.gov/primer/bar-code-medication-administration",
         "AHRQ PSNet Primer — Bar Code Medication Administration",
         "Clinical Workflows"),
        ("clinical-ahrq-medication-errors.txt",
         "https://psnet.ahrq.gov/primer/medication-errors-and-adverse-drug-events",
         "AHRQ PSNet Primer — Medication Errors and ADEs",
         "Clinical Workflows"),
        ("clinical-ahrq-falls-primer.txt",
         "https://psnet.ahrq.gov/primer/falls",
         "AHRQ PSNet Primer — Falls",
         "Clinical Workflows"),
        ("clinical-ahrq-restraints-primer.txt",
         "https://psnet.ahrq.gov/primer/restraints",
         "AHRQ PSNet Primer — Restraints",
         "Clinical Workflows"),
        ("clinical-ahrq-rapid-response.txt",
         "https://psnet.ahrq.gov/primer/rapid-response-systems",
         "AHRQ PSNet Primer — Rapid Response Systems",
         "Clinical Workflows"),
        ("clinical-ahrq-handoffs-clinical.txt",
         "https://psnet.ahrq.gov/primer/communication-between-clinicians",
         "AHRQ PSNet Primer — Communication Between Clinicians",
         "Clinical Workflows"),
        ("clinical-cdc-sepsis-data.txt",
         "https://www.cdc.gov/sepsis/data-research/index.html",
         "CDC — Sepsis Data and Research",
         "Clinical Workflows"),
        ("clinical-cdc-hai.txt",
         "https://www.cdc.gov/healthcare-associated-infections/index.html",
         "CDC — Healthcare-Associated Infections",
         "Clinical Workflows"),
        ("clinical-ismp-high-alert.txt",
         "https://www.ismp.org/recommendations/high-alert-medications-acute-list",
         "ISMP — High-Alert Medications in Acute Care",
         "Clinical Workflows"),
    ],
    "cross_module": [
        ("cross-charge-capture-clinical-events.txt",
         "https://medcaremso.com/charge-capture-clinical-events/",
         "Charge Capture from Clinical Events — Workflow Integration",
         "Cross-Module"),
        ("cross-fhir-to-cerner-data-flow.txt",
         "https://6b.health/insight/fhir-cerner-data-integration/",
         "FHIR-to-Cerner Data Flow Patterns",
         "Cross-Module"),
        ("cross-pharmacy-nursing-order-routing.txt",
         "https://www.tactionsoft.com/blog/cerner-pharmacy-nursing-orders/",
         "Pharmacy and Nursing Order Routing in Cerner",
         "Cross-Module"),
        ("cross-clinical-revenue-integration.txt",
         "https://cerecore.net/clinical-revenue-cycle-integration/",
         "Clinical and Revenue Cycle Integration — CereCore",
         "Cross-Module"),
        ("cross-workflow-optimization.txt",
         "https://www.ghit.digital/insight/detail/cerner-workflow-optimization",
         "Cerner Workflow Optimization Across Modules",
         "Cross-Module"),
        ("cross-fhir-charge-billing.txt",
         "https://medcaremso.com/fhir-charge-billing-integration/",
         "FHIR-Based Charge and Billing Integration",
         "Cross-Module"),
        ("cross-clinical-decision-support.txt",
         "https://ehrenhancify.com/cerner-clinical-decision-support/",
         "Cerner Clinical Decision Support — Cross-Module Workflow",
         "Cross-Module"),
        ("cross-hl7-v2-millennium.txt",
         "https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185",
         "HL7 v2 Messaging — Cerner Millennium Integration",
         "Cross-Module"),
    ],
}

MODULE_DIR = {
    "millennium": "millennium",
    "powerchart": "powerchart",
    "revenue_cycle": "revenue_cycle",
    "clinical": "clinical",
    "cross_module": "millennium",  # cross-module files routed to millennium dir; tagged via overrides
}


def _strip_html(html: str) -> str:
    """Remove nav, footer, header, script, style, and extract text."""
    if not _BS4:
        # Crude fallback
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    soup = BeautifulSoup(html, "html.parser")
    # Wikipedia: main content is in #mw-content-text — extract that and skip the rest.
    main = soup.select_one("#mw-content-text") or soup.select_one("main") or soup.select_one("article")
    if main is not None:
        # Remove obvious chrome inside the main content
        for tag in main(["script", "style", "noscript", "iframe", "form"]):
            tag.decompose()
        for el in main.select(".navbox, .infobox, .sidebar, .reference, .mw-editsection, "
                              ".thumbcaption, .hatnote, .mbox, .mw-references-wrap"):
            try:
                el.decompose()
            except Exception:
                pass
        text = main.get_text(separator="\n")
    else:
        for tag in soup(["script", "style", "nav", "footer", "noscript", "iframe", "form"]):
            tag.decompose()
        # Remove obvious banner/cookie chrome but be conservative — don't blanket-strip
        # anything containing 'menu' or 'nav' since that breaks Wikipedia/AHRQ content
        # whose semantic class names sometimes include those substrings.
        for el in soup.select("[class*='cookie'], [class*='consent'], [id*='cookie'], "
                              "[id*='consent'], [class*='subscribe-banner'], "
                              "[class*='cookie-banner'], [aria-label*='cookie'], "
                              "[aria-label*='consent']"):
            try:
                el.decompose()
            except Exception:
                pass
        text = soup.get_text(separator="\n")
    # Collapse runs of blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


_ERROR_PAGE_MARKERS = [
    "A PHP Error was encountered",
    "404 Not Found",
    "Page not found",
    "page you are looking for does not exist",
    "404 - Not Found",
    "this page isn't available",
    "Error 404",
    "Sorry, we couldn't find that page",
    "Severity: Notice",
    "Severity: Warning",
    "Fatal error:",
    "doesn't exist",
    "DNS_PROBE_FINISHED",
    "Just a moment...",  # cloudflare challenge
]


def fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ct = resp.headers.get("Content-Type", "")
        body = resp.read()
        if "application/pdf" in ct or body[:4] == b"%PDF":
            raise ValueError("PDF content (skipping — needs separate handling)")
        text = body.decode("utf-8", errors="replace")
        # Soft 404 / error page detection — server returned 200 but body says "not found"
        head_lower = text[:8000].lower()
        for marker in _ERROR_PAGE_MARKERS:
            if marker.lower() in head_lower:
                raise ValueError(f"soft 404 / error page (matched '{marker}')")
        return text


def write_doc(out_path: str, title: str, url: str, module_label: str, body: str) -> None:
    header = (
        f"# SOURCE: {title}\n"
        f"# URL: {url}\n"
        f"# MODULE: {module_label}\n"
        f"# RETRIEVED: {TODAY}\n"
        f"# ---\n\n"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + body + "\n")


def run_module(module_key: str) -> dict:
    if module_key not in TARGETS:
        print(f"Unknown module: {module_key}. Choose from: {list(TARGETS)}")
        return {}
    targets = TARGETS[module_key]
    out_dir = os.path.join(DATA_DIR, MODULE_DIR[module_key])
    os.makedirs(out_dir, exist_ok=True)

    results = {"ok": [], "short": [], "fail": []}
    for fname, url, title, label in targets:
        out_path = os.path.join(out_dir, fname)
        try:
            raw = fetch(url)
        except urllib.error.HTTPError as exc:
            print(f"  FAIL  {fname}  HTTP {exc.code}  {url}")
            results["fail"].append((fname, f"HTTP {exc.code}"))
            continue
        except urllib.error.URLError as exc:
            print(f"  FAIL  {fname}  URL  {exc.reason}  {url}")
            results["fail"].append((fname, f"URL {exc.reason}"))
            continue
        except Exception as exc:
            print(f"  FAIL  {fname}  {type(exc).__name__}  {exc}")
            results["fail"].append((fname, str(exc)))
            continue

        cleaned = _strip_html(raw)
        words = len(cleaned.split())
        if words < 300:
            print(f"  SHORT {fname}  ({words} words)")
            results["short"].append((fname, words))
            continue

        write_doc(out_path, title, url, label, cleaned)
        print(f"  OK    {fname}  ({words:,} words)")
        results["ok"].append((fname, words))
        time.sleep(0.5)  # be polite

    print()
    print(f"  {len(results['ok'])} written, {len(results['short'])} too short, {len(results['fail'])} failed")
    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch_phase2_module.py <module>")
        print(f"Modules: {list(TARGETS)}")
        sys.exit(1)
    mod = sys.argv[1].lower().replace("-", "_")
    if mod == "all":
        for m in TARGETS:
            print(f"\n=== {m} ===")
            run_module(m)
    else:
        run_module(mod)


if __name__ == "__main__":
    main()
