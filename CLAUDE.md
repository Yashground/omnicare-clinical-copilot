# OmniCare Clinical Copilot — Claude Code Guide

## Project Overview

OmniCare is an AI-powered clinical assistant that automates medical documentation and real-time patient monitoring. It uses a **multi-agent architecture** with Google Cloud medical AI models, persistent storage via Firestore, and real FHIR/DICOM servers via the Healthcare API.

**Core pipeline (v2 — multi-agent):**
1. Audio input → Whisper ASR → Transcript + HeAR cough detection → SOAP note
2. Scenario/Synthea data → FHIR store (Healthcare API) → Vitals monitoring + anomaly detection
3. Medical images → DICOM store (Healthcare API) → MedGemma radiology report
4. All stages aggregated → Discharge summary + ICD-10 codes
5. All data persisted in Firestore with agent activity logs

**Agents:**
- `ConsultationAgent` — Audio → Transcript → SOAP note
- `HeARAgent` — Audio → Respiratory event detection (cough, wheeze) → Clinical suggestions
- `VitalsMonitorAgent` — FHIR vitals → Anomaly detection → Admission note
- `RadiologyAgent` — Medical images → Radiology report
- `DischargeAgent` — Aggregate all → Discharge summary + ICD-10
- `ClinicalOrchestrator` — Coordinates all agents, manages encounter lifecycle

---

## Repository Structure

```
medlm/
├── notebooks/
│   ├── 00_setup_and_models.ipynb       # Load models (MedGemma, Whisper, HeAR), init cloud services
│   ├── 01_consultation_audio_soap.ipynb # ConsultationAgent + HeARAgent
│   ├── 02_admission_vitals_fhir.ipynb   # VitalsMonitorAgent + real FHIR store
│   ├── 03_radiology_dicom_imaging.ipynb # RadiologyAgent + real DICOM store
│   ├── 04_discharge_summary.ipynb       # DischargeAgent + ICD-10 + export
│   └── utils/
│       ├── __init__.py
│       ├── agents.py               # Multi-agent framework (5 agents + orchestrator)
│       ├── firestore_db.py         # Firestore-backed persistence (patients, encounters, vitals, meds)
│       ├── healthcare_api.py       # Google Cloud Healthcare API (FHIR + DICOM stores)
│       ├── hear_helpers.py         # HeAR model loading, audio segmentation, cough detection
│       ├── patient_simulator.py    # Dynamic patient scenarios (replaces hardcoded data)
│       ├── encounter_state.py      # Facade: delegates to Firestore or local JSON fallback
│       ├── fhir_helpers.py         # FHIR bundle parsing and extraction
│       ├── dicom_helpers.py        # DICOM image loading and Orthanc helpers
│       ├── mcp_tools.py            # Model inference wrappers (transcribe, SOAP, admission, etc.)
│       └── prompts.py              # System/user prompt templates for all stages
├── src/
│   ├── backend/
│   │   ├── omnicare-mcp.js        # Express HTTP + MCP stdio server (legacy)
│   │   └── package.json
│   ├── frontend/
│   │   └── index.html              # Browser-based ambient listening UI
│   └── scripts/
│       ├── test_audio.py           # E2E client: WAV → /api/transcribe
│       ├── mock_client.py          # Simulates encounter by streaming text chunks
│       ├── synthea_vitals_streamer.py  # Reads Synthea FHIR bundles, streams vitals
│       ├── direct_asr.py           # Direct MedASR endpoint test
│       ├── setup_synthea.js        # Downloads Synthea v3.3.0 JAR
│       ├── get_token.js            # Generates GCP bearer token
│       └── convert.ps1             # FFmpeg: MP3 → 16kHz mono WAV
├── synthea-mcp/
│   ├── src/index.ts                # TypeScript MCP server for Synthea
│   └── package.json
├── data/                           # Sample audio files (MP3, WAV)
├── output/fhir/                    # Synthea-generated FHIR JSON output
└── synthea-with-dependencies.jar   # Synthea binary (182 MB, do not delete)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Notebook runtime | Google Colab (T4 GPU) |
| Medical LLM | MedGemma 1.5-4b-it (4-bit quantized via bitsandbytes) |
| Speech-to-text | Whisper Large v3 Turbo |
| Cough detection | HeAR (google/hear-pytorch) — 512-dim health acoustic embeddings |
| Database | Google Cloud Firestore (persistent encounter/patient storage) |
| FHIR server | Google Cloud Healthcare API (FHIR R4 store) |
| DICOM server | Google Cloud Healthcare API (DICOM store + DICOMweb) |
| Agent framework | Custom Python agents (utils/agents.py) |
| Patient simulation | Dynamic scenarios (utils/patient_simulator.py) |
| Backend (legacy) | Node.js + Express.js + MCP protocol |
| Synthetic data | Synthea v3.3.0 (Java JAR) |
| Auth | Google Cloud ADC + Colab auth.authenticate_user() |

---

## Cloud Services Configuration

### GCP Project Setup
```bash
# Set in Colab secrets or environment:
GCP_PROJECT_ID=your-project-id
HEALTHCARE_LOCATION=us-central1
HEALTHCARE_DATASET=omnicare-dataset
```

### Required GCP APIs
```bash
gcloud services enable healthcare.googleapis.com
gcloud services enable firestore.googleapis.com
```

### Firestore
- Automatically initialized by `firestore_db.py`
- Collections: `patients`, `encounters` (with subcollections: `vitals`, `medications`, `conditions`, `agent_logs`)
- Falls back to local JSON if Firestore unavailable

### Healthcare API
- Dataset: `omnicare-dataset` (auto-created)
- FHIR Store: `omnicare-fhir` (R4, auto-created)
- DICOM Store: `omnicare-dicom` (auto-created)
- All stores created idempotently by `healthcare_api.setup_healthcare_stores()`

---

## Running the Notebooks

### Full pipeline (recommended)
```
1. Open 00_setup_and_models.ipynb — loads all models, inits cloud services
2. Open 01_consultation_audio_soap.ipynb — consultation + HeAR analysis
3. Open 02_admission_vitals_fhir.ipynb — FHIR vitals + admission note
4. Open 03_radiology_dicom_imaging.ipynb — radiology report
5. Open 04_discharge_summary.ipynb — discharge + ICD-10 + export
```

### Key session variables (from Notebook 00)
- `orchestrator` — ClinicalOrchestrator instance
- `models` — dict of all loaded models
- `medgemma_model`, `medgemma_processor` — MedGemma LLM
- `asr_pipeline` — Whisper ASR
- `hear_model`, `hear_preprocess` — HeAR model

### Patient scenarios
5 built-in clinical scenarios (selectable per encounter):
- `pneumonia_diabetic` — John Smith, productive cough + diabetes
- `chest_pain_cardiac` — Maria Garcia, chest pain + CAD
- `copd_exacerbation` — Robert Chen, COPD exacerbation
- `uti_elderly` — Dorothy Williams, UTI + diabetes
- `asthma_pediatric_adult` — Aisha Patel, asthma exacerbation

---

## Multi-Agent Architecture

```
ClinicalOrchestrator
├── ConsultationAgent  (Whisper + MedGemma → SOAP)
├── HeARAgent          (HeAR → cough detection → MedGemma suggestion)
├── VitalsMonitorAgent (FHIR → anomaly detection → admission note)
├── RadiologyAgent     (MedGemma multimodal → radiology report)
└── DischargeAgent     (aggregate → discharge summary + ICD-10)
```

- All agents share models via the `models` dict
- State shared through Firestore (encounter document + subcollections)
- Each agent logs actions to `encounters/{id}/agent_logs` for auditability
- Orchestrator can run agents individually or as a full pipeline

---

## HeAR Integration

Google's HeAR (Health Acoustic Representations) model detects respiratory events:
- **Input**: 2-second audio clips at 16kHz mono
- **Output**: 512-dim embeddings → classified as cough, breathing, etc.
- **Pipeline**: Audio → segment into 2s clips → HeAR embeddings → cosine similarity to cough centroid → events
- **Clinical interpretation**: HeAR events + transcript → MedGemma → clinical suggestion
- **Integration point**: Runs during consultation phase alongside Whisper ASR

---

## Legacy Backend (src/backend/)

The Node.js Express + MCP server is preserved for backward compatibility:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/transcribe` | Audio/text → MedASR → MedGemma SOAP |
| `POST` | `/api/fhir/observation` | FHIR Observation logging stub |

### MCP Tools
- `generate_synthea_data(patientCount, state)` — runs Synthea JAR

---

## Key Architectural Decisions

- **Multi-agent over monolith**: Each clinical phase has a dedicated agent with clear inputs/outputs
- **Firestore over JSON files**: Persistent, queryable storage for drugs, vitals, conditions per patient
- **Healthcare API over self-hosted**: Managed FHIR/DICOM stores instead of HAPI FHIR/Orthanc containers
- **HeAR for acoustic monitoring**: Detects cough/respiratory events that may not appear in speech transcription
- **Dynamic scenarios over hardcoded data**: 5 diverse clinical scenarios with MedGemma-generated transcripts
- **Firestore fallback**: encounter_state.py auto-delegates to local JSON if Firestore is unavailable
- **Agent audit trail**: All agent actions logged to Firestore for observability

---

## Known Issues / TODOs

- HeAR cough classifier needs calibration data (currently uses energy-based fallback)
- ICD-10 coding uses keyword matching — should integrate ICD-10 MCP tool for real lookups
- Legacy Express backend still has hardcoded endpoint IDs
- No authentication on Express routes (notebook pipeline uses GCP auth)
- DICOM upload requires actual DICOM files (PNG/JPG images skip DICOMweb upload)

---

## Dependencies

### Notebook (Colab)
- `transformers`, `accelerate`, `bitsandbytes` — Model loading
- `torch` — PyTorch runtime
- `soundfile`, `librosa` — Audio processing
- `pydicom`, `Pillow` — Medical image handling
- `google-cloud-firestore` — Firestore client
- `google-api-python-client`, `google-auth` — Healthcare API
- `huggingface_hub` — Gated model access

### Backend (`src/backend/package.json`)
- `@google-cloud/vertexai`, `express`, `google-auth-library`
- `@modelcontextprotocol/sdk`, `dotenv`, `zod`

### System dependencies
- Java — for Synthea JAR
- FFmpeg — for audio conversion
- Google Cloud SDK (`gcloud`) — for auth and API enablement
