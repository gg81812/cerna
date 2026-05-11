# Golden Set SME Review Package — 2026-04-20
**For:** Cerner-certified SME (clinical workflows + Millennium technical)  
**From:** Cerna project team, Accenture Oracle Health practice  
**Purpose:** Validate expected keyword lists before Gate 2 evaluation  
**Deadline:** 2026-04-26 (before uCern access decision)

---

## Background and Why This Matters

Cerna's performance is measured by **keyword hit rate (KHR)**: the fraction of `expected_keywords` found in the system's response. A query passes (KHR ≥ 0.70) if at least 70% of expected keywords appear in the answer.

The current baseline is **73.3% overall pass rate**. This number is used to determine whether Cerna is ready to demo. However, some failures may be **false negatives** — the system gave a correct answer, but that answer didn't use the exact vocabulary in the expected keyword list.

**Before we can trust the baseline, a Cerner SME needs to review each keyword list and confirm:**
1. Is this keyword genuinely required in a correct answer?
2. Could a correct answer express this concept differently (synonym, paraphrase)?
3. Is the system's actual response correct despite missing the keyword?

**Your instructions:** For each keyword, mark: **KEEP** (required), **REMOVE** (not required for a correct answer), or **REPLACE: [alternative keyword]** (the concept is required but this word isn't the right one).

If you find any missing queries — things a Cerner user would commonly ask that aren't covered — add them in the "Proposed Additions" section at the end.

---

## How to Read This Document

Each query section shows:
- The question
- Expected keywords (the eval criterion)
- The system's actual response excerpt
- Missing keywords (the ones that caused a FAIL, if applicable)
- A review prompt asking for your judgment

> **Important:** Do NOT review queries marked "TPD failure" — the system didn't answer at all due to infrastructure limits. Those queries will be re-run. Only review queries where the system produced a real response.

---

## Section 1: Clinical Module (15 Queries)

---

### clin-001 — TPD FAILURE — Skip

**Query:** "What is eMAR in Cerner?"  
**Status:** Infrastructure failure (Groq daily quota). System returned an error, not an answer. **Do not review.**

---

### clin-002 — PASS (KHR 0.80) — Optional Review

**Query:** "What is BCMA in Cerner?"  
**Expected keywords:** `BCMA`, `barcode`, `medication`, `administration`, `patient safety`  
**Missing:** `patient safety`  
**System response excerpt:** "BCMA is a critical component of Cerner's clinical workflow, ensuring safe and accurate medication administration. It involves scanning a patient's wristband and the medication barcode to verify…"

**SME Review question:** The response clearly describes medication safety through scanning. Does a correct BCMA definition require the exact phrase "patient safety"? Could "safe medication administration" or "safety checks" satisfy this criterion?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `patient safety` | KEEP / REMOVE / REPLACE | |

---

### clin-003 — PASS (KHR 1.00) — No review needed

**Query:** "What is PharmNet in Cerner?"  
All 5 keywords found. ✅

---

### clin-004 — TPD FAILURE — Skip

**Query:** "What is FirstNet in Cerner?"  
Infrastructure failure. **Do not review.**

---

### clin-005 — PASS (KHR 0.80) — Optional Review

**Query:** "What is SurgiNet in Cerner?"  
**Expected keywords:** `SurgiNet`, `surgical`, `perioperative`, `OR`, `Cerner`  
**Missing:** `perioperative`  
**System response excerpt:** "SurgiNet in Cerner is the Scheduling module (also called Cerner Scheduling or SurgiNet Scheduling for surgical cases) that provides appointment scheduling, resource management, and patient flow management for outpatient clinics, procedural areas…"

**SME Review question:** The response discusses surgical scheduling and OR management. Is "perioperative" specifically required in a correct SurgiNet definition, or does "surgical" + "OR" + "scheduling" adequately cover the concept?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `perioperative` | KEEP / REMOVE / REPLACE | |

---

### clin-006 — TPD FAILURE — Skip

**Query:** "How does the eMAR medication administration workflow work in Cerner?"  
Infrastructure failure. **Do not review.**

---

### clin-007 — PASS (KHR 0.857) — Optional Review

**Query:** "What are the steps for BCMA scanning during medication administration?"  
**Expected keywords:** `BCMA`, `scan`, `barcode`, `patient`, `medication`, `nurse`, `wristband`  
**Missing:** `nurse`  
**System response excerpt:** "The BCMA workflow involves scanning the medication barcode and the patient wristband to ensure accurate and safe medication administration. According to the clinical-medication-administration-record source, the process requires scanning a patient's wristband and the medication barcode…"

**SME Review question:** The response describes the scanning workflow but doesn't use the word "nurse." Is a BCMA scanning workflow description incomplete without specifying that nurses perform it? Or is the workflow description sufficient without naming the role?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `nurse` | KEEP / REMOVE / REPLACE | |

---

### clin-008 — TPD FAILURE — Skip

**Query:** "How does scheduling work in Cerner for outpatient appointments?"  
Infrastructure failure. **Do not review.**

---

### clin-009 — TPD FAILURE — Skip

**Query:** "How is discharge planning documented in Cerner clinical workflows?"  
Infrastructure failure. **Do not review.**

---

### clin-010 — PASS (KHR 1.00) — No review needed

**Query:** "How does PharmNet handle medication dispensing in inpatient settings?"  
All 6 keywords found. ✅

---

### clin-011 — PASS (KHR 0.714) — Optional Review

**Query:** "What patient safety events can be reported through Cerner clinical workflows?"  
**Expected keywords:** `patient safety`, `event`, `report`, `clinical`, `Cerner`, `nursing`, `incident`  
**Missing:** `nursing`, `incident`  
**System response excerpt:** "Cerner's primary offering for patient safety event reporting is the RL6 (Risk & Compliance) module, which integrates with Millennium clinical data. This module allows users to report patient safety events including adverse drug events, falls, pressure injuries, near misses…"

**SME Review question:** The response describes patient safety event reporting through RL6 (Risk & Compliance). Does a correct answer to this question require: (a) the word "nursing" specifically — or is "clinical" + "users" sufficient? (b) the word "incident" specifically — or does "events", "adverse events", "near misses" cover the concept?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `nursing` | KEEP / REMOVE / REPLACE | |
| `incident` | KEEP / REMOVE / REPLACE | |

---

### clin-012 — TPD FAILURE — Skip

**Query:** "How does nursing documentation work in PowerChart for clinical assessments?"  
Infrastructure failure. **Do not review.**

---

### clin-013 — PASS (KHR 0.714) — Optional Review

**Query:** "How do you configure eMAR to support complex multi-step medication protocols?"  
**Expected keywords:** `eMAR`, `protocol`, `multi-step`, `medication`, `configuration`, `Cerner`, `order`  
**Missing:** `configuration`, `Cerner`, `order`  
**System response excerpt:** "To configure eMAR to support complex multi-step medication protocols, you'll need to create a custom protocol in the eMAR module. This involves defining the steps and actions required for the medication administration process. You can do this by navigating to PowerChart > Clinical…"

**SME Review question:** The response says "configure eMAR" and "create a custom protocol" but doesn't use the words "configuration" or "order" explicitly. (a) Is "configure" equivalent to "configuration" for keyword purposes? (b) Does a correct answer about multi-step medication protocols require the word "order" (as in medication order), or is "protocol" + "steps" sufficient?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `configuration` | KEEP / REMOVE / REPLACE | Suggestion: `configure` would satisfy |
| `Cerner` | KEEP / REMOVE / REPLACE | |
| `order` | KEEP / REMOVE / REPLACE | |

---

### clin-014 — FAIL (KHR 0.143) — Review Required

**Query:** "What are the build steps to configure BCMA overrides and exception workflows?"  
**Expected keywords:** `BCMA`, `override`, `exception`, `build`, `configuration`, `workflow`, `Cerner`  
**Missing:** `BCMA`, `override`, `exception`, `build`, `configuration`, `workflow` (6/7 missing)  
**System response:** "I'm not sure which Cerner topic you're asking about. Here are some related searches — click one to get a full answer."  

**Note:** This is a genuine retrieval failure — the KB does not contain a "BCMA overrides build configuration" document. The system fell into a "Did You Mean" path.

**SME Review question (two questions):**
1. Is "BCMA override/exception workflow build" a real, documented Cerner build task? If yes, what is the correct source document (uCern page, Cerner documentation section)?
2. If this is a real build task, should it remain in the evaluation set and we source the documentation? Or should this query be removed as too niche for the current KB scope?

| Decision | Notes |
|----------|-------|
| KEEP this query / REMOVE this query | |
| Source document for KB if KEEP: | |

---

### clin-015 — FAIL (KHR 0.667) — Review Required

**Query:** "How does Cerner's AI-powered PowerChart AI feature assist with clinical documentation?"  
**Expected keywords:** `PowerChart AI`, `clinical documentation`, `AI`, `assistance`, `ambient`, `Cerner`  
**Missing:** `assistance`, `ambient`  
**System response excerpt:** "PowerChart AI assists with clinical documentation by analyzing patient-clinician conversations in real-time, extracting clinical entities, and generating structured clinical notes following PowerChart's specific template formats…"

**SME Review question:** (a) The word "ambient" refers to ambient clinical intelligence (AI listening to patient-clinician conversations). The response describes this capability but doesn't use the word "ambient." Is "ambient" a required term in a correct description of PowerChart AI, or is the functional description sufficient? (b) The word "assistance" — the response says "assists" (verb form). Is the noun "assistance" required, or should the verb "assists" count?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `ambient` | KEEP / REMOVE / REPLACE | |
| `assistance` | KEEP / REMOVE / REPLACE | Suggestion: `assist` or `assists` would satisfy |

---

## Section 2: Millennium Module (15 Queries)

---

### mil-001 — PASS (KHR 0.80) — Optional Review

**Query:** "What is the Cerner Millennium platform?"  
**Expected keywords:** `Millennium`, `platform`, `clinical`, `Oracle Health`, `domain`  
**Missing:** `Oracle Health`, `domain`  
**System response excerpt:** "The Cerner Millennium platform is an enterprise-class EHR platform that serves 27,000+ clients worldwide across 35+ countries. It has various key modules, including PowerChart for clinical documentation and CPOE, FirstNet for emergency department tracking…"

**SME Review question:** (a) The response says "Cerner Millennium" but doesn't use "Oracle Health" (the rebranded name). Is "Oracle Health" a required term in a correct Cerner Millennium platform description? (b) The response describes key modules and architecture but doesn't use "domain." Is "domain" required in a basic platform overview answer?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `Oracle Health` | KEEP / REMOVE / REPLACE | |
| `domain` | KEEP / REMOVE / REPLACE | |

---

### mil-002 — PASS (KHR 0.80) — Optional Review

**Query:** "What is CCL scripting in Cerner?"  
**Expected keywords:** `CCL`, `Cerner Command Language`, `scripting`, `Discern`, `queries`  
**Missing:** `Discern`, `queries`  
**System response excerpt:** "CCL scripting in Cerner refers to the use of Cerner Command Language (CCL), a proprietary, SQL-like scripting language used within the Cerner Millennium platform to create reports, extract clinical and financial data, build batch jobs…"

**SME Review question:** The response defines CCL fully but doesn't mention "Discern" (the reporting module that uses CCL) or "queries" by name. (a) Is "Discern" required in a CCL definition — or is Discern primarily covered by its own question (mil-004)? (b) Is the word "queries" required in a CCL scripting definition, or does "create reports", "extract data", "SQL-like" sufficiently describe the use?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `Discern` | KEEP / REMOVE / REPLACE | |
| `queries` | KEEP / REMOVE / REPLACE | |

---

### mil-003 — PASS (KHR 0.80) — Optional Review

**Query:** "What are MPages in Cerner Millennium?"  
**Expected keywords:** `MPages`, `workflow`, `provider`, `clinical`, `component`  
**Missing:** `provider`  
**System response excerpt:** "MPages (Millennium Pages) are customizable, web-based clinical views embedded within PowerChart and other Cerner Millennium applications. They extend the core EHR by allowing developers and organizations to build purpose-built clinical workflow components…"

**SME Review question:** The response describes MPages as used by "developers and organizations" but doesn't use "provider." Is "provider" (as in clinician/provider-facing) a required term in a correct MPages description?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `provider` | KEEP / REMOVE / REPLACE | |

---

### mil-004 — PASS (KHR 0.80) — Optional Review

**Query:** "What is Discern Analytics?"  
**Expected keywords:** `Discern`, `analytics`, `reporting`, `CCL`, `queries`  
**Missing:** `CCL`, `queries`  
**System response excerpt:** "Discern Analytics is Cerner Millennium's integrated reporting and business intelligence platform. It enables healthcare organizations to create custom reports, perform ad-hoc data mining, build operational dashboards, and extract data from the Millennium clinical and financial data…"

**SME Review question:** The response describes reporting and data mining but doesn't use "CCL" or "queries." Is CCL a required component of a Discern Analytics definition? Discern Analytics is often used via CCL, but the definition question might not require mentioning CCL.

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `CCL` | KEEP / REMOVE / REPLACE | |
| `queries` | KEEP / REMOVE / REPLACE | |

---

### mil-005 — FAIL (KHR 0.60) — Review Required

**Query:** "What is the Millennium domain architecture?"  
**Expected keywords:** `domain`, `architecture`, `Millennium`, `nodes`, `services`  
**Missing:** `nodes`, `services`  
**System response excerpt:** "The Millennium domain architecture consists of three primary tiers: Application, Database, and Interface. The Application Tier is responsible for handling clinical transactions, with key server types including PRISMNODE, MCP, MPSERVER, and CVLINK…"

**SME Review question (important):** The response mentions "PRISMNODE, MCP, MPSERVER, CVLINK" — these ARE nodes/server types. (a) Does the presence of "PRISMNODE" count as the keyword "nodes" being present? (b) Does a correct Millennium architecture answer require the word "services" (as in server services or Windows services), or is "server types" equivalent? If "PRISMNODE" should count as "nodes," this is a keyword-matching limitation in the eval, not a system failure.

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `nodes` | KEEP / REMOVE / REPLACE | Suggestion: `PRISMNODE` or `server` would satisfy |
| `services` | KEEP / REMOVE / REPLACE | Suggestion: `server types` would satisfy |

---

### mil-006 — FAIL (KHR 0.667) — Review Required

**Query:** "How do I configure a CCL report to query patient visit data?"  
**Expected keywords:** `CCL`, `ENCOUNTER`, `PERSON`, `select`, `query`, `report`  
**Missing:** `ENCOUNTER`, `PERSON`, `select`  
**System response excerpt:** "To configure a CCL report to query patient visit data, you'll need to use the Discern Explorer module in Millennium. This module allows you to create, edit, and execute CCL scripts. To start, navigate to PowerChart > Millennium > Discern Explorer…"

**SME Review question:** The expected keywords `ENCOUNTER` and `PERSON` refer to specific Cerner Millennium table names in the CCL database schema. (a) Is knowing the exact table names (ENCOUNTER, PERSON) required for a correct answer to "how do I configure a CCL report to query patient visit data?" Or is describing the workflow to create a CCL report sufficient? (b) Is "select" (as in SQL SELECT statement) required in a correct workflow answer — or is it more of a CCL programmer-level detail?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `ENCOUNTER` | KEEP / REMOVE / REPLACE | |
| `PERSON` | KEEP / REMOVE / REPLACE | |
| `select` | KEEP / REMOVE / REPLACE | |

---

### mil-007 — PASS (KHR 1.00) — No review needed

**Query:** "What are the steps to build a custom MPages component?"  
All 5 keywords found. ✅ *(Note: response had a JSON parse artifact — raw JSON in response — but keywords were still present)*

---

### mil-008 — PASS (KHR 1.00) — No review needed

**Query:** "How does Millennium handle user authentication and single sign-on?"  
All 5 keywords found. ✅

---

### mil-009 — PASS (KHR 0.80) — Optional Review

**Query:** "What is the difference between a Millennium domain and a node?"  
**Expected keywords:** `domain`, `node`, `environment`, `Millennium`, `architecture`  
**Missing:** `environment`  
**System response excerpt:** "A Millennium domain and a node are two related but distinct concepts in the Cerner EHR architecture. A domain represents the complete EHR instance, encompassing applications, databases, and build data. On the other hand, a node is a single server process…"

**SME Review question:** The response contrasts domain vs. node but doesn't use "environment." Is "environment" required here (e.g., "test environment / production environment")? Or is the domain/node distinction sufficient without "environment" terminology?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `environment` | KEEP / REMOVE / REPLACE | |

---

### mil-010 — TPD FAILURE — Skip

**Query:** "How do I upgrade a Cerner Millennium environment?"  
Infrastructure failure. **Do not review.**

---

### mil-011 — PASS (KHR 0.80) — Optional Review

**Query:** "What is OCI hosting and how does it apply to Millennium?"  
**Expected keywords:** `OCI`, `Oracle Cloud Infrastructure`, `hosting`, `Millennium`, `migration`  
**Missing:** `migration`  
**System response excerpt:** "OCI hosting in Millennium refers to Oracle Cloud Infrastructure (OCI) hosting the Millennium platform. This means that Millennium instances are hosted on Oracle Cloud Infrastructure with Oracle-managed compute, storage, and networking. This change impacts integrations, requiring…"

**SME Review question:** The response describes OCI hosting in detail but doesn't use the word "migration." Is "migration" required in an OCI hosting explanation (because customers migrating to OCI is the context)? Or is it optional since the question asks "what is OCI hosting" rather than "how do I migrate"?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `migration` | KEEP / REMOVE / REPLACE | |

---

### mil-012 — FAIL (KHR 0.60) — Review Required

**Query:** "How are code sets used in Cerner Millennium?"  
**Expected keywords:** `code set`, `code value`, `nomenclature`, `Millennium`, `configuration`  
**Missing:** `nomenclature`, `configuration`  
**System response excerpt:** "code sets are used to map internal Cerner code values to standard terminologies like LOINC. This is crucial for message transformation, as lab results may include both internal Cerner code values and standard terminologies like LOINC…"

**SME Review question:** (a) "Nomenclature" is Cerner-specific terminology for the code set management table. Is "nomenclature" required in a correct code set explanation — or is the mapping/configuration concept sufficient without the exact table name? (b) Is "configuration" required here — or is the system's description of code set usage (mapping internal codes to terminologies) sufficient?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `nomenclature` | KEEP / REMOVE / REPLACE | |
| `configuration` | KEEP / REMOVE / REPLACE | |

---

### mil-013 — PASS (KHR 0.833) — Optional Review

**Query:** "How do you implement a custom Discern rule to fire clinical alerts in Millennium?"  
**Expected keywords:** `Discern`, `rule`, `alert`, `clinical`, `CCL`, `event`  
**Missing:** `event`  
**System response excerpt:** "To implement a custom Discern rule to fire clinical alerts in Millennium, you'll need to create a new CCL program in Discern Explorer…"

**SME Review question:** The response describes the implementation without using "event" explicitly. Is "event" required (as in "event-driven alert" or "event firing") — or does "fire clinical alerts" cover this adequately?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `event` | KEEP / REMOVE / REPLACE | |

---

### mil-014 — PASS (KHR 1.00) — No review needed

**Query:** "What are the performance tuning best practices for CCL queries on large patient populations?"  
All 6 keywords found. ✅

---

### mil-015 — FAIL (KHR 0.667) — Review Required

**Query:** "How does Cerner Millennium manage multi-facility data partitioning?"  
**Expected keywords:** `facility`, `partition`, `encounter`, `organization`, `Millennium`, `multi-facility`  
**Missing:** `encounter`, `organization`  
**System response excerpt:** "Cerner Millennium manages multi-facility data partitioning through the use of Community MRN (CMRN) for cross-facility patient identification. When CMRN is not available, a facility-to-MRN mapping is maintained. This ensures that data is associated with the correct patient context…"

**SME Review question:** The response describes Community MRN and facility mapping but doesn't use "encounter" or "organization." (a) Is "encounter" (patient visit record) required in a multi-facility partitioning explanation? (b) Is "organization" required here — or is "facility" equivalent in Cerner terminology?

| Keyword | Decision | Alternative (if REPLACE) |
|---------|----------|-------------------------|
| `encounter` | KEEP / REMOVE / REPLACE | |
| `organization` | KEEP / REMOVE / REPLACE | |

---

## Section 3: Proposed Query Additions

If there are common Cerner questions not covered in the evaluation set above, please list them here:

| Module | Proposed Question | Why it matters |
|--------|------------------|----------------|
| Clinical | | |
| Millennium | | |

---

## SME Contact and Timeline

**Reviewer name:** _______________  
**Cerner certification / role:** _______________  
**Review completed by:** 2026-04-26 (uCern access decision date)  
**Submit to:** [Project lead email]

**If review cannot be completed by 2026-04-26:** The 73.3% baseline stands as the formal Gate 2 baseline with documented limitations. Do not attempt keyword list changes without SME input.

---

*Package prepared: 2026-04-20 · Phase 2 Week 5 · Cerna Backend Verification*
