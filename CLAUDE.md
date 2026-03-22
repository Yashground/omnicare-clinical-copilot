# OmniCare Clinical Copilot — Claude Code Guide

## Project Overview

OmniCare is an AI-powered clinical assistant MVP that automates medical documentation and real-time patient monitoring. It bridges local clinical data (audio, vitals) to Google Cloud medical AI models (MedASR, MedGemma) deployed on Vertex AI.

**Core pipeline:**
1. Audio input → MedASR (Google Cloud medical ASR) → Transcription
2. Transcription → MedGemma (medical LLM on Vertex AI) → SOAP note
3. Synthea FHIR bundles → vitals streamer → `/api/fhir/observation`
4. MCP tools → AI agent tool-calling surface

---

## Repository Structure

```
medlm/
├── src/
│   ├── backend/
│   │   ├── omnicare-mcp.js       # Main server: Express HTTP + MCP stdio server
│   │   └── package.json
│   └── scripts/
│       ├── test_audio.py          # E2E client: WAV → /api/transcribe → saves output
│       ├── mock_client.py         # Simulates encounter by streaming text chunks
│       ├── synthea_vitals_streamer.py  # Reads Synthea FHIR bundles, streams vitals
│       ├── direct_asr.py          # Direct MedASR endpoint test
│       ├── setup_synthea.js       # Downloads Synthea v3.3.0 JAR
│       ├── get_token.js           # Generates GCP bearer token → token.txt
│       └── convert.ps1            # FFmpeg: MP3 → 16kHz mono WAV
├── synthea-mcp/
│   ├── src/index.ts               # TypeScript MCP server exposing Synthea tools
│   ├── build/index.js             # Compiled output
│   └── package.json
├── data/                          # Sample audio files (MP3, WAV)
├── docs/
│   └── medgemma_output.md         # Generated SOAP note output (auto-written)
├── output/fhir/                   # Synthea-generated FHIR JSON output
└── synthea-with-dependencies.jar  # Synthea binary (182 MB, do not delete)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend runtime | Node.js v18+ (ESM modules) |
| HTTP framework | Express.js 5.x |
| AI/ML | Google Cloud MedASR + MedGemma via Vertex AI |
| MCP protocol | `@modelcontextprotocol/sdk` |
| Auth | `google-auth-library` (Application Default Credentials) |
| Synthetic data | Synthea v3.3.0 (Java JAR) |
| Scripts | Python 3.9+ |
| Audio processing | FFmpeg (16kHz mono WAV required by MedASR) |
| TypeScript tooling | `tsc` (synthea-mcp only) |

---

## Environment Configuration

The backend reads from `.env` in `src/backend/`. Required variables:

```env
PROJECT_ID=32142846166
LOCATION_ASR=europe-west1
ENDPOINT_ID_ASR=mg-endpoint-d6a4a403-d834-4a85-ba9c-439648042ba0
LOCATION_LLM=europe-west4
ENDPOINT_ID_LLM=mg-endpoint-6a2cdec4-6429-4edc-a0b4-6081749e0696
PORT=3000
```

> **Note:** Endpoint IDs and Project IDs are currently hardcoded in `omnicare-mcp.js` (lines 28–31, 92–94). The `.env` file is loaded but the constants override it. Refactoring to use `process.env` is a known TODO.

**GCP Authentication:** Uses Application Default Credentials. Run once before starting:
```bash
gcloud auth application-default login
```

---

## Running the Project

### Start the backend server
```bash
cd src/backend
npm install
node omnicare-mcp.js
# Express listens on http://localhost:3000
# MCP server also starts via stdio
```

### Run the E2E audio pipeline
```powershell
# Step 1: Convert audio to 16kHz mono WAV (if needed)
./src/scripts/convert.ps1

# Step 2: Run full pipeline (WAV → MedASR → MedGemma → SOAP note)
python src/scripts/test_audio.py
# Output saved to docs/medgemma_output.md
```

### Other test clients
```bash
# Simulate encounter with text chunks (no audio required)
python src/scripts/mock_client.py

# Stream FHIR vitals from a Synthea output file
python src/scripts/synthea_vitals_streamer.py output/fhir/<bundle>.json

# Direct MedASR test (bypasses Express)
python src/scripts/direct_asr.py
```

### Synthea MCP server
```bash
cd synthea-mcp
npm install
npm run build    # compile TypeScript
npm start        # runs MCP server via stdio
```

### Download/refresh Synthea JAR
```bash
node src/scripts/setup_synthea.js
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/transcribe` | Accepts `{ encounter_id, text_chunk?, audio_chunk? }`. If `audio_chunk` (base64 WAV), calls MedASR. Accumulates transcript; triggers MedGemma SOAP after >3 sentences. |
| `POST` | `/api/fhir/observation` | Accepts FHIR Observation resource. Logs vital sign. Stub for GCP Healthcare API integration. |

### MCP Tools

**omnicare-mcp** (stdio):
- `generate_synthea_data(patientCount, state)` — runs Synthea JAR, outputs to `./output/fhir/`

**synthea-mcp** (stdio):
- `generate_patient_population(count, state)` — same as above, TypeScript implementation
- `list_generated_patients` — lists FHIR JSON files in `./output/fhir/`

---

## Key Architectural Decisions

- **Dual transport**: The main server runs both Express (HTTP) and MCP (stdio) simultaneously. Express handles scripted clients; MCP handles AI agent tool-calling.
- **Encounter state in memory**: `encounterTranscripts` is a plain in-memory object keyed by `encounter_id`. No persistence — restarts clear all state.
- **SOAP trigger heuristic**: MedGemma is called when the accumulated transcript has more than 3 sentence-boundary periods. This is intentionally simple for the MVP.
- **MedASR payload format**: MedASR expects `{ "file": "<base64>" }` directly — not wrapped in a Vertex AI `instances[]` array (unlike MedGemma).
- **MedGemma payload format**: Uses `@requestFormat: "chatCompletions"` with a system + user message structure, `max_tokens: 1024`.
- **Audio requirement**: MedASR requires 16kHz mono WAV. Use `convert.ps1` (FFmpeg) to normalize any other format.

---

## Known Issues / TODOs

- Endpoint IDs and Project IDs are hardcoded in `omnicare-mcp.js` — should be moved to `process.env`
- `encounterTranscripts` state is lost on server restart — no database persistence
- FHIR observation endpoint is a logging stub only — GCP Healthcare API integration is commented out
- No authentication on Express routes
- `test_audio.wav` must be pre-generated (run `convert.ps1` on the ElevenLabs MP3 first)

---

## Dependencies

### Backend (`src/backend/package.json`)
- `@google-cloud/vertexai` — Vertex AI client
- `@modelcontextprotocol/sdk` — MCP protocol
- `express` — HTTP server
- `google-auth-library` — GCP OAuth/ADC
- `dotenv` — env file loading
- `zod` — schema validation for MCP tools

### synthea-mcp (`synthea-mcp/package.json`)
- `@modelcontextprotocol/sdk` — MCP protocol
- `zod` — schema validation
- `typescript` (dev) — compilation

### Python scripts (no requirements.txt — install manually)
```bash
pip install requests
```

### System dependencies
- Java (any version) — required to run `synthea-with-dependencies.jar`
- FFmpeg — required for audio conversion (`convert.ps1`)
- Google Cloud SDK (`gcloud`) — required for ADC auth
