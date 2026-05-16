# OmniCare Clinical Copilot — MVP Architecture Design

**Date:** 2026-05-16
**Scope:** MVP — Core consultation loop (Audio → Transcript + HeAR → SOAP note)
**Stack:** Google ADK · Vertex AI Agent Engine · RunPod GPU Endpoints · Firestore

---

## 1. Overall Architecture

Three-tier system: frontend · Agent Engine · RunPod model endpoints.

```
┌─────────────────────────────────────────────────────┐
│                      Frontend                        │
│                   Web app                            │
│     Audio capture → REST calls → Display results    │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS (REST + SSE streaming)
┌────────────────────▼────────────────────────────────┐
│           Cloud Run Proxy                            │
│   Auth + signed GCS URLs + REST ↔ Agent Engine API  │
└────────────────────┬────────────────────────────────┘
                     │ GCP IAM (streamQuery)
┌────────────────────▼────────────────────────────────┐
│           Vertex AI Agent Engine                     │
│                                                      │
│  ClinicalOrchestrator (LlmAgent / root)              │
│  └── ConsultationPipeline (SequentialAgent)          │
│      ├── TranscriptionAgent                          │
│      ├── HeARAgent                                   │
│      └── SOAPAgent                                   │
└────────────────────────────────────────────────────┬─┘
                                                     │ HTTP (OpenAI-compat API)
┌────────────────────────────────────────────────────▼─┐
│              RunPod Serverless GPU Endpoints          │
│  ┌─────────────────┐  ┌────────┐  ┌───────────────┐  │
│  │ MedGemma 4B-IT  │  │Whisper │  │     HeAR      │  │
│  │  (vLLM worker)  │  │(custom │  │(custom worker)│  │
│  │                 │  │worker) │  │               │  │
│  └─────────────────┘  └────────┘  └───────────────┘  │
└───────────────────────────────────────────────────────┘
         │                                │
┌────────▼────────┐            ┌──────────▼────────────┐
│   Firestore     │            │  Google Healthcare API │
│ (encounter +    │            │  FHIR store (phase 2)  │
│  patient data)  │            │  DICOM store (phase 2) │
└─────────────────┘            └───────────────────────┘
```

Firestore holds encounter data durably. Healthcare API (FHIR/DICOM) is already configured but dormant for MVP — wired in for phase 2.

---

## 2. RunPod Model Endpoints

Three separate serverless endpoints, each serving one model:

| Endpoint name | Model | Worker type | GPU | Response contract |
|---------------|-------|-------------|-----|-------------------|
| `whisper-asr` | Whisper Large v3 Turbo | Custom handler | 16GB (RTX 4080) | `{ transcript, language, duration_s }` |
| `hear-detector` | HeAR (google/hear-pytorch) | Custom handler | 8GB (RTX 3080) | `{ events: [{type, start_s, confidence}] }` |
| `medgemma-llm` | MedGemma 1.5 4B-IT (`google/medgemma-1.5-4b-it`) | vLLM worker | 24GB (RTX 3090) | OpenAI-compatible chat completions |

**Notes:**
- MedGemma uses RunPod's built-in vLLM worker — set `MODEL_NAME=google/medgemma-1.5-4b-it`, point ADK at the OpenAI-compatible URL. Zero custom code.
- Whisper and HeAR need custom RunPod workers (`runpod.serverless.start()` + handler, ~30 lines each).
- All three scale to zero when idle. A periodic keep-warm ping eliminates cold starts during active clinic hours.
- Each endpoint returns a clean JSON contract; agents never parse raw model output.

---

## 3. ADK Agent Structure & Session State

### Repository layout

```
medlm/
├── notebooks/              # existing prototype — kept for reference, not modified
├── backend/                # production ADK backend
│   ├── omnicare/           # ADK agent package
│   │   ├── agent.py        # exposes root_agent (ClinicalOrchestrator)
│   │   ├── agents/
│   │   │   ├── orchestrator.py    # ClinicalOrchestrator (LlmAgent)
│   │   │   ├── consultation.py    # ConsultationPipeline (SequentialAgent)
│   │   │   ├── transcription.py   # TranscriptionAgent (LlmAgent)
│   │   │   ├── hear.py            # HeARAgent (LlmAgent)
│   │   │   └── soap.py            # SOAPAgent (LlmAgent)
│   │   ├── tools/
│   │   │   ├── runpod_whisper.py  # call_whisper() tool
│   │   │   ├── runpod_hear.py     # call_hear() tool
│   │   │   ├── runpod_medgemma.py # call_medgemma() tool
│   │   │   └── firestore.py       # save_encounter(), get_encounter() tools
│   │   └── config.py              # endpoint URLs, env vars
│   ├── workers/
│   │   ├── whisper_worker.py      # RunPod custom worker for Whisper
│   │   └── hear_worker.py         # RunPod custom worker for HeAR
│   ├── scripts/
│   │   └── deploy.py              # Vertex AI Agent Engine deployment script
│   └── requirements.txt
├── frontend/               # separate frontend codebase
├── specs/                  # architecture specs
└── data/                   # existing sample audio files
```

### Session state keys

`session.state` is the shared handoff mechanism between all agents in a session:

| Key | Written by | Read by | Value |
|-----|-----------|---------|-------|
| `encounter_id` | Orchestrator | All agents | `str` |
| `patient_id` | Orchestrator | SOAPAgent, Firestore tool | `str` |
| `audio_url` | Frontend (input) | TranscriptionAgent, HeARAgent | `gs://bucket/audio.wav` |
| `transcript` | TranscriptionAgent | SOAPAgent | `str` |
| `language` | TranscriptionAgent | SOAPAgent | `str` (e.g. `"en"`) |
| `hear_events` | HeARAgent | SOAPAgent | `[{type, start_s, confidence}]` |
| `soap_note` | SOAPAgent | Firestore tool, frontend | `{S, O, A, P}` |
| `encounter_saved` | SOAPAgent | Orchestrator | `bool` |

Each agent reads only its required keys and writes only its output keys. No agent touches another agent's keys.

---

## 4. API Contract (Frontend ↔ Backend)

A thin **Cloud Run proxy** sits between the browser and Vertex AI Agent Engine. It handles GCP IAM auth, translates the simple REST contract below into Agent Engine API calls, and issues signed GCS upload URLs. The frontend never talks to Agent Engine directly.

**Local dev:** `adk api_server` exposes these same endpoints — no proxy needed during development.

### Start a session
```
POST /sessions
Body:    { "user_id": "dr-smith", "patient_id": "p-123" }
Returns: { "session_id": "sess-abc..." }
```

### Run the consultation pipeline
```
POST /sessions/{session_id}/query
Body:    { "message": "Start consultation", "audio_url": "gs://bucket/audio.wav" }
Returns: SSE stream ending with:
         { "transcript": "...", "hear_events": [...], "soap_note": { S, O, A, P } }
```

### Get session state
```
GET /sessions/{session_id}/state
Returns: full session.state dict
```

### Get a signed GCS upload URL
```
GET /upload-url?patient_id=p-123&filename=audio.wav
Returns: { "upload_url": "https://storage.googleapis.com/...", "gcs_uri": "gs://..." }
```

**Audio handling:** Frontend uploads audio directly to GCS using the signed URL, then passes the `gs://` URI in the query body. No binary data travels through the agent API.

---

## 5. End-to-End Data Flow

```
1.  Frontend uploads audio → GCS (signed URL)
2.  Frontend POST /sessions/{id}/query  { audio_url: "gs://..." }

3.  ClinicalOrchestrator receives message
    └── routes to ConsultationPipeline (SequentialAgent)

4.  TranscriptionAgent
    ├── calls call_whisper(audio_url)  → RunPod Whisper endpoint
    ├── writes session.state["transcript"]
    └── writes session.state["language"]

5.  HeARAgent  (reads audio_url from state)
    ├── calls call_hear(audio_url)  → RunPod HeAR endpoint
    └── writes session.state["hear_events"]

6.  SOAPAgent
    ├── reads transcript + hear_events from state
    ├── calls call_medgemma(prompt)  → RunPod MedGemma endpoint
    ├── writes session.state["soap_note"]
    └── calls save_encounter()  → Firestore

7.  Agent Engine streams final state back to frontend
8.  Frontend renders SOAP note + flagged respiratory events
```

### Latency estimate

| Step | Warm | Cold start |
|------|------|------------|
| Audio upload to GCS | 1–3s | 1–3s |
| Whisper transcription | 5–15s | +15s |
| HeAR detection | 2–5s | +10s |
| MedGemma SOAP generation | 5–10s | +20s |
| **Total** | **12–28s** | **40–65s** |

Cold starts occur only after idle periods. A keep-warm ping every 30s on RunPod endpoints eliminates cold starts during active clinic hours.

---

## 6. Phase 2 Expansion

Adding vitals monitoring, radiology, and discharge agents requires no restructuring — each is additive:

```python
# MVP
root_agent = LlmAgent(sub_agents=[consultation_pipeline])

# Phase 2 — extend the orchestrator
root_agent = LlmAgent(
    sub_agents=[
        consultation_pipeline,   # unchanged
        vitals_agent,            # new: reads FHIR → writes vitals_summary
        radiology_agent,         # new: reads DICOM → writes radiology_report
        discharge_agent,         # new: aggregates all state → discharge summary + ICD-10
    ]
)
```

Each new agent = one new file in `agents/`, one new file in `tools/`, one new entry in `sub_agents`.

---

## 7. Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Agent framework | Google ADK | Native Vertex AI integration, built for multi-agent, extensible |
| Orchestration pattern | SequentialAgent pipeline | Clean handoffs via session.state, easy to extend |
| LLM deployment | RunPod serverless vLLM | Own the GPU, OpenAI-compat API, scales to zero |
| ASR/HeAR deployment | RunPod custom workers | Not chat-completion models, need custom handlers |
| Backend hosting | Vertex AI Agent Engine | Managed, no containers, native GCP auth + Firestore |
| Storage | Firestore | Already integrated, persistent, queryable |
| Audio transfer | GCS + signed URLs | Avoids binary in REST body, fast upload, reusable across agents |
| Frontend/backend split | Clean REST + SSE contract | Parallel development without tight coupling |

---

## 8. Out of Scope (MVP)

- Vitals monitoring (VitalsMonitorAgent + FHIR) — Phase 2
- Radiology reports (RadiologyAgent + DICOM) — Phase 2
- Discharge summary + ICD-10 (DischargeAgent) — Phase 2
- Frontend authentication (GCP IAM on backend from day 1) — Phase 2
- Keep-warm infrastructure for RunPod endpoints — add if latency SLA requires it
