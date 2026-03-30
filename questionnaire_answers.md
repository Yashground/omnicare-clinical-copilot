# OmniCare Clinical Copilot — Questionnaire Answers

---

## Q1: Estimate the total financial impact you expect to achieve by the end of your project. Consider time savings for resources (per week).

**Answer:** 30 – 40 hours

**Explanation:**

OmniCare automates 5 major clinical documentation workflows that are currently manual and time-intensive:

| Automated Task | Agent | Manual Time | Automated Time | Weekly Savings |
|---|---|---|---|---|
| SOAP Note Writing | ConsultationAgent | ~20 min/patient × 20 pts/day | ~3 min review/patient | ~28 hrs/week |
| Admission Notes | VitalsMonitorAgent | ~25 min/admission × 5/week | ~5 min review | ~1.5 hrs/week |
| Vitals Anomaly Detection | VitalsMonitorAgent | Continuous manual chart review | Automated real-time alerts | ~3–5 hrs/week |
| Radiology Reports | RadiologyAgent | ~15 min/report × 10/week | ~5 min review | ~1.5 hrs/week |
| Discharge Summaries + ICD-10 Coding | DischargeAgent | ~40 min/discharge × 5/week | ~10 min review | ~2.5 hrs/week |
| Respiratory Monitoring (cough/wheeze) | HeARAgent | Manual auscultation or missed | Automated detection | ~1–2 hrs/week |

**Conservative total: ~35–40 hrs/week** per clinical team.

The estimate is capped at 30–40 (not >40) because:
- The project is MVP-stage (HeAR needs calibration, ICD-10 uses keyword matching)
- Clinicians still must review and approve all AI-generated notes
- Not every agent runs on every patient every encounter

At department-level scale (3+ physicians), savings would exceed 40 hrs/week easily.

---

## Q2: Consider cost savings for programs and processes (per year, in EUR).

**Answer:** 100k – 500k

**Explanation:**

The cost savings derive from clinician time reclaimed and operational efficiency gains:

| Cost Driver | Calculation | Annual Savings (EUR) |
|---|---|---|
| Clinician time savings | 35 hrs/week × 52 weeks × ~€80/hr (avg physician cost) | ~€145,600 |
| Reduced transcription service costs | Replaces outsourced medical transcription (~€0.10/line, thousands of lines/week) | ~€30,000–50,000 |
| Faster discharge turnaround | Reduced length-of-stay by 0.5 days/patient × bed cost ~€500/day × ~200 discharges/yr | ~€50,000 |
| Reduced coding errors (ICD-10) | Fewer claim rejections/resubmissions (~2% rejection rate × revenue impact) | ~€20,000–40,000 |
| Avoided adverse events (vitals anomaly detection) | Earlier deterioration detection → fewer ICU escalations (~€5k–10k/event × ~5–10/yr) | ~€25,000–100,000 |

**Conservative total: ~€270k–€385k/year** for a single clinical unit.

This lands in the 100k–500k range rather than higher because:
- MVP-stage product (not yet department-wide deployment)
- ICD-10 coding is keyword-based (limited billing accuracy gains)
- HeAR respiratory detection still needs calibration
- Savings assume a single clinical team, not hospital-wide rollout

At multi-department scale, it would easily exceed €500k.

---

## Q3: What is the expected total added revenue (per year, in EUR) from your project's implementation?

**Answer:** 10k – 100k

**Explanation:**

OmniCare is primarily a **cost-savings and efficiency tool**, not a direct revenue generator. However, there are indirect revenue impacts:

| Revenue Driver | Mechanism | Annual Revenue Impact (EUR) |
|---|---|---|
| Improved ICD-10 coding accuracy | Better documentation → captures previously under-coded encounters (~5% uplift) | ~€25,000–50,000 |
| Faster discharge turnaround | Reduced bed-days → increased patient throughput (~1 extra patient/week × avg €2,000) | ~€50,000–100,000 |
| Reduced claim rejections | Better documentation quality → fewer payer denials (~2% rejection rate recovered) | ~€10,000–20,000 |

**Estimated range: ~€85k–€170k/year** — but with caveats that bring the defensible figure toward the lower band.

Why 10k–100k and not 100k–500k:
- Revenue uplift is indirect (throughput, coding) — no new product/service being sold
- ICD-10 coding is currently keyword-based, limiting real billing accuracy improvements
- The throughput gain depends on discharge being the actual bottleneck (often it isn't)
- No SaaS licensing or commercialization revenue is built into the current MVP
- Added revenue is speculative and harder to attribute directly to the tool vs. other factors

The project's core value proposition is **cost avoidance and time savings** (Q1/Q2), not revenue generation.

---

## Q4: Do you currently have a customer Net Promoter Score (NPS)?

**Answer:** No / Not applicable

**Explanation:**

OmniCare Clinical Copilot is currently an MVP/prototype stage project running on Google Colab notebooks. It has not been deployed to real end-users (clinicians) in a production setting, so:

- No real clinician users have used the system in practice yet
- No user feedback surveys or NPS measurements have been conducted
- The 5 built-in patient scenarios use synthetic/simulated data (Synthea), not real patient encounters
- The frontend ambient listening UI is a proof-of-concept, not a deployed product

An NPS score would become relevant after pilot deployment with actual clinical staff reviewing AI-generated SOAP notes, admission notes, and discharge summaries against their manual workflow.

---

## Q5: How many people do you expect your project to impact?

**Answer:** 100 – 1,000

**Explanation:**

The impact spans several stakeholder groups:

| Stakeholder Group | Who | Estimated Count |
|---|---|---|
| Clinicians (direct users) | Physicians, residents, attending doctors using the tool | 10–30 |
| Nursing & clinical support staff | Nurses reviewing admission notes, vitals alerts, discharge instructions | 30–60 |
| Medical coders / billing | Staff receiving auto-generated ICD-10 codes and discharge summaries | 5–15 |
| Radiology technicians | Staff reviewing AI-generated radiology reports | 5–10 |
| Patients (indirect beneficiaries) | Patients receiving faster, more accurate documentation and quicker discharges | 200–500/year |
| IT / DevOps | Teams managing GCP infrastructure, Firestore, Healthcare API | 3–5 |
| Clinical leadership | Department heads using audit trails and analytics for quality oversight | 5–10 |

**Total: ~260–630 people impacted**

Why 100–1,000 and not higher:
- The MVP targets a single clinical unit or department, not hospital-wide
- Patient count scales with deployment scope — a single unit sees ~200–500 patients/year
- Not yet at multi-hospital or health-system level where it would reach 1,000–4,000+

Why not <100:
- Even a single-unit deployment impacts clinicians + nurses + support staff + patients
- The patient population alone pushes the count well past 100 annually

---

## Q6: Have you identified and addressed all applicable compliance obligations for this initiative?

**Answer:** No

**Explanation:**

OmniCare handles sensitive clinical/medical data, and several compliance obligations have been identified but not yet fully addressed in the current MVP:

| Compliance Area | Status | Details |
|---|---|---|
| HIPAA | Identified, not addressed | No data anonymization; synthetic patient names/MRNs in Firestore without field-level encryption; no BAA with GCP |
| GDPR | Identified, not addressed | No data subject access/deletion workflows; no consent management |
| Medical Device Regulation (MDR/EU) | Identified, not addressed | AI-generated clinical outputs not assessed for regulatory classification; no CE marking |
| Data encryption | Partially addressed | GCP provides encryption at rest/transit by default; no field-level encryption for PHI |
| Authentication & Authorization | Not addressed | Legacy Express backend has no API auth; no multi-tenant access controls or RBAC |
| Audit Trail | Addressed | Agent audit logs in Firestore (agent_logs subcollection) with timestamps — compliance strength |
| Model Governance | Not addressed | No model validation framework; no bias testing; MedGemma outputs not validated against clinical gold standard |

Key gaps: No HIPAA BAA, no data anonymization pipeline, no regulatory classification of AI clinical outputs, unauthenticated Express endpoints, no formal risk assessment. "No" is the honest answer — obligations are identified but implementation is incomplete at MVP stage.

Note: ~70% of technical compliance gaps (auth, encryption, anonymization, BAA) are addressable by project end. Formal regulatory classification (MDR/CE) remains out of scope for the MVP.

---

## Q7: What is your current execution progress?

**Answer:** 51 – 75%, advanced execution

**Explanation:**

Based on the repository analysis, here is the per-component status:

| Component | Status | Completeness |
|---|---|---|
| Multi-agent framework (5 agents + orchestrator) | Fully implemented in agents.py | 100% |
| All 5 pipeline notebooks (00–04) | Built and functional | 95% |
| Full pipeline notebook (omnicare_full_pipeline.ipynb) | Consolidated single-notebook version | 100% |
| Utility modules (10 Python files) | All implemented and integrated | 90% |
| MedGemma integration (SOAP, admission, radiology, discharge) | Working with 4-bit quantization | 90% |
| Whisper ASR with medical vocabulary priming | Working | 95% |
| HeAR respiratory detection | Implemented but needs calibration data | 60% |
| Firestore persistence + local JSON fallback | Fully working with auto-fallback | 95% |
| Healthcare API (FHIR + DICOM stores) | Implemented with idempotent setup | 85% |
| 5 patient scenarios | Built with dynamic transcript generation | 100% |
| Frontend ambient UI | Proof of concept, functional | 70% |
| Legacy Express backend | Working but needs auth + parameterization | 60% |
| ICD-10 coding | Keyword-based only — needs ontology integration | 40% |
| Compliance & security | Audit trail done; auth, encryption, anonymization not done | 25% |
| Clinical validation | Not started — no real clinician testing | 0% |
| Production deployment | Not started — Colab-only | 0% |

**Weighted estimate: ~65%** — solidly in "advanced execution." The core AI pipeline (consultation → admission → radiology → discharge) is built and functional end-to-end. What remains is hardening (compliance, auth, ICD-10), validation (clinician testing), and deployment (beyond Colab).

---

## Q8: How does your project or idea differ from previous approaches?

**Answer:** Significant change to the existing approach

**Explanation:**

Comparison of OmniCare vs. existing clinical documentation solutions:

| Aspect | Existing Approaches | OmniCare's Approach |
|---|---|---|
| Architecture | Monolithic single-model pipelines (one ASR → one note generator) | Multi-agent (5 agents + orchestrator), independently testable and auditable |
| Audio analysis | Speech-to-text only (Dragon Medical, Nuance DAX) | Speech-to-text (Whisper) + non-verbal respiratory detection (HeAR) — captures cough/wheeze that transcription misses |
| Clinical scope | Single-stage tools (transcription OR notes OR coding — never unified) | End-to-end: Consultation → Admission → Radiology → Discharge + ICD-10, one coordinated flow |
| Medical imaging | Separate radiology AI systems, not linked to encounter context | MedGemma multimodal with prior clinical context (SOAP + admission notes inform the report) |
| Data persistence | Typically local/session-based | Dual-backend (Firestore + local JSON fallback) with FHIR R4 and DICOM via Healthcare API |
| Patient simulation | Hardcoded test data | Dynamic transcript generation from clinical scenarios using MedGemma |

Why "Significant change" and not "Fundamentally new":
- Individual components exist in the market (ASR, clinical NLP, radiology AI, ICD-10 coding)
- Innovation is in combining and orchestrating them as a multi-agent pipeline with shared state
- HeAR integration for non-verbal acoustic monitoring is novel in this context, but HeAR itself is an existing model
- Uses existing standards (FHIR, DICOM) in a new coordination pattern

Why not "Incremental enhancement":
- Multi-agent architecture for clinical documentation is genuinely uncommon
- Combining speech + non-verbal acoustic analysis in a single encounter is not standard practice
- End-to-end audio-to-discharge with ICD-10 goes beyond any single existing tool's scope
- Dual-persistence fallback and agent audit trail add architectural novelty

---

## Q9: To what extent does your project address the main challenge or opportunity?

**Answer:** Solves root cause within one area or delivers significant improvement

**Explanation:**

The root cause problem: Clinicians spend 1–2 hours per day on documentation instead of patient care. This stems from manual, disconnected workflows — dictating notes, writing admissions, interpreting images, drafting discharge summaries, and coding diagnoses are all separate, repetitive tasks.

| Impact Level | What it would mean | OmniCare's fit? |
|---|---|---|
| Only addresses symptoms | Just speeds up one step (e.g., faster typing) | No |
| Partially tackles root cause | Automates transcription but still needs manual note writing | No |
| **Solves root cause within one area** | **Automates full documentation lifecycle end-to-end within a clinical unit** | **Yes** |
| Solves root cause across all areas | Transforms hospital-wide operations, billing, scheduling, staffing | No |

Within the clinical documentation domain, OmniCare addresses the root cause comprehensively:
- Audio → structured SOAP notes (eliminates manual transcription + note writing)
- FHIR vitals → anomaly detection → admission notes (eliminates manual chart review)
- Medical images → radiology reports with clinical context (eliminates disconnected imaging analysis)
- Aggregate → discharge summary + ICD-10 (eliminates most time-consuming documentation task)
- HeAR detects non-verbal cues the manual process misses entirely (net-new capability)

Why not "across all areas" or "transformative":
- Scope limited to documentation — doesn't address clinical decision support, drug interactions, scheduling, or billing beyond ICD-10
- Covers one clinical unit, not hospital-wide operations
- Still requires clinician review/approval (AI-assist, not full autonomy)
- ICD-10 coding is keyword-based (not full revenue cycle transformation)

---

## Q10: How broad is the cross-functional collaboration in your project?

**Answer:** Active collaboration across multiple functions

**Explanation:**

OmniCare spans multiple clinical and technical functions by design:

| Function | How It's Involved | Evidence in Codebase |
|---|---|---|
| Clinical / Medical | SOAP note structure, admission/discharge formats, vital sign ranges, ICD-10 | prompts.py, agents.py (NORMAL_RANGES), patient_simulator.py |
| AI / Data Science | Model selection (MedGemma, Whisper, HeAR), quantization, prompt engineering | mcp_tools.py, hear_helpers.py, agents.py |
| Cloud Engineering / DevOps | GCP Healthcare API (FHIR/DICOM), Firestore, auth, infra setup | healthcare_api.py, firestore_db.py, encounter_state.py |
| Health Informatics / Standards | FHIR R4 resources, DICOM metadata, LOINC/SNOMED CT, ICD-10 | fhir_helpers.py, dicom_helpers.py, patient_simulator.py |
| Frontend / UX | Ambient listening UI, real-time audio capture for clinicians | src/frontend/index.html (Web Audio API) |
| Backend Engineering | Express server, MCP protocol, API design | omnicare-mcp.js, synthea-mcp/src/index.ts |

Why "Active collaboration" and not "Fully integrated end-to-end across value chain":
- Doesn't yet extend into billing/revenue cycle, administration, supply chain, or staffing
- No formal integration with existing EHR systems (Epic, Cerner) yet
- Clinical validation by real practitioners hasn't happened yet

Why not "Limited cross-functional":
- Genuinely requires and integrates 6+ distinct domain functions
- Not just an AI model — touches clinical workflows, health data standards, cloud infra, and frontend UX
- Multi-agent architecture itself forces cross-functional thinking (each agent maps to a different clinical function)

---

## Q11: What problem-solving approaches have you used in your project?

**Answer:** Design Thinking, Root Cause Analysis, Agile/Scrum

**Explanation:**

| Approach | Applicable? | Evidence from the Project |
|---|---|---|
| **Design Thinking** | Yes | User-centered pipeline mirrors actual clinician workflow (consultation → admission → imaging → discharge). Ambient listening UI designed for hands-free use. 5 patient scenarios simulate real clinical personas. |
| **Root Cause Analysis** | Yes | Root cause identified: clinicians lose hours to fragmented manual documentation. Each agent eliminates a specific bottleneck. Multi-agent architecture itself is an outcome of decomposing the problem into 5 distinct root causes. |
| **Agile/Scrum** | Yes | Iterative evolution from monolithic Express backend (v1, legacy) to multi-agent notebooks (v2). Modular architecture (each agent = independent deliverable). Notebooks structured as incremental working increments (00→01→02→03→04). |
| Lean/Six Sigma | No | No waste-reduction metrics or statistical quality controls |
| Kaizen | No | No continuous small improvements tracking |
| PDCA Cycle | Partially | Notebook progression resembles PDCA but not formalized |
| Theory of Constraints | No | No systematic bottleneck identification framework |
| A3 Problem Solving | No | No single-page structured problem reports |

---

## Q12: How significantly has your project simplified processes or structures?

**Answer:** Clear simplification (reduced steps, reduced handovers)

**Explanation:**

| Workflow | Before (Manual) | After (OmniCare) | Steps Eliminated |
|---|---|---|---|
| Consultation → SOAP | Dictate → Transcribe → Review → Write SOAP → File (5 steps, 2 handovers) | Speak → AI transcript + SOAP → Review (2 steps, 0 handovers) | 3 steps, 2 handovers |
| Vitals → Admission | Nurse records → EHR entry → Doctor reviews chart → Writes note (4 steps, 2 handovers) | FHIR auto-ingest → Auto-flag anomalies → Auto-generate note → Review (2 steps, 0 handovers) | 2 steps, 2 handovers |
| Imaging → Report | Capture → Send to radiologist → Write report → Send to attending → Integrate (5 steps, 3 handovers) | Upload → MedGemma report with context → Review (2 steps, 0 handovers) | 3 steps, 3 handovers |
| Discharge | Aggregate notes → Write summary → Code ICD-10 → Billing (4 steps, 2 handovers) | Auto-aggregate → Auto-summary + ICD-10 → Review (2 steps, 0 handovers) | 2 steps, 2 handovers |

Why "Clear simplification" not "Structural complexity eliminated":
- Clinician review step still required (AI-assist, not full autonomy)
- Doesn't eliminate underlying organizational structure (departments, roles still exist)
- Simplifies within documentation but doesn't restructure clinical care delivery

---

## Q13: How does artificial intelligence contribute to your project's impact?

**Answer:** AI enables capability not previously possible

**Explanation:**

| AI Capability | What It Enables | Previously Possible? |
|---|---|---|
| HeAR respiratory detection | Detects coughs/wheezes from audio that speech transcription ignores — parallel non-verbal clinical signal | No — no workflow captures non-verbal acoustic biomarkers during consultations |
| MedGemma multimodal radiology | Generates radiology reports incorporating prior clinical context (SOAP + admission), not just image in isolation | No — existing radiology AI tools analyze images independently |
| Dynamic transcript generation | Creates realistic doctor-patient conversations from scenario seeds for testing | No — previously required actors or static scripts |
| Real-time ambient SOAP generation | Hands-free background audio → structured clinical notes while doctor focuses on patient | Emerging but not with full SOAP structure |
| End-to-end encounter lifecycle | Single pipeline: audio → discharge + ICD-10 with shared state across all stages | No — no existing system coordinates 5 AI models across full encounter |

Why the highest level: HeAR non-verbal acoustic analysis is a genuinely new clinical capability. Without AI (MedGemma, Whisper, HeAR), none of the core functionality works at all — AI is foundational, not supplementary.

---

## Q14: Is your project scalable across different domains or functions?

**Answer:** Yes

**Explanation:**

OmniCare's architecture is inherently scalable across multiple clinical domains:

| Scalability Dimension | How It Adapts | Effort |
|---|---|---|
| Other clinical depts (Cardiology, Oncology, etc.) | Swap scenarios in patient_simulator.py, adjust NORMAL_RANGES, update prompts | Low — config only |
| Other hospital sites | Same GCP infra scales automatically; point to new FHIR/DICOM stores | Low — infra config |
| Primary care / outpatient | SOAP pipeline works identically; skip admission/radiology agents if not needed | Low — use agent subset |
| Telehealth / remote | Ambient UI already browser-based; audio capture works over any connection | Low — already supported |
| Non-English markets | Whisper supports 99+ languages; update medical vocabulary prompt | Medium — localization |
| Mental health / psychiatry | Replace SOAP with psychiatric templates; HeAR could detect speech patterns | Medium — new templates |
| Emergency / triage | VitalsMonitorAgent anomaly detection directly applicable for triage | Low — adjust thresholds |
| Research / clinical trials | Firestore audit trail + FHIR store provide structured data for analysis | Low — data already structured |

Key architectural enablers:
- Modular agents — departments can use 1, 3, or all 5 agents as needed
- Configurable scenarios — template-driven; adding a specialty = adding a new scenario dict
- Cloud-native persistence — Firestore and Healthcare API auto-scale
- Standard protocols — FHIR R4 and DICOM are universal, not proprietary
- General-purpose models — MedGemma, Whisper, HeAR are not fine-tuned to one specialty

---

## Q15: Is it possible to increase the quantity or scale of the initial pilot?

**Answer:** Yes, with some adjustments

**Explanation:**

| Scaling Dimension | Feasibility | Adjustments Required |
|---|---|---|
| More users (clinicians) | Easy | Currently single-user Colab. Need: multi-user auth, concurrent sessions, RBAC. Firestore already supports concurrent writes. |
| More patient scenarios | Easy | Add new scenario dicts to patient_simulator.py — template-driven, no code changes. |
| More hospital locations | Medium | Each site needs own FHIR/DICOM store or shared with namespacing. Need: multi-tenant config. |
| Higher patient volume | Medium | Colab GPU session limits (12–24 hrs). Need: migrate to persistent GPU infra (Cloud Run, GKE, or Vertex AI endpoints). |
| More clinical specialties | Easy | Add prompt templates, normal ranges, scenarios. Modular agents = no architectural changes. |
| Real-time streaming (simultaneous consultations) | Hard | Current batch model. Need: async queue, model serving (vLLM/Triton), WebSocket connections. |
| EHR integration (Epic, Cerner) | Hard | No FHIR write-back implemented. Need: HL7 FHIR integration layer, vendor API credentials. |

Why "with some adjustments" not "easily":
- Colab runtime is the primary bottleneck — ephemeral, single-user, time-limited GPU sessions
- No multi-tenant auth for simultaneous clinicians
- Batch processing, not streaming — parallel encounters need queuing infrastructure

Why not "No":
- Underlying architecture (modular agents, Firestore, Healthcare API, FHIR/DICOM) is cloud-scalable
- Adding scenarios, specialties, locations is low-effort
- Work needed is infrastructure/deployment, not architectural redesign

---
