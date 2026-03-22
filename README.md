# OmniCare Clinical Copilot MVP

OmniCare is an AI-powered clinical assistant designed to automate medical documentation and real-time patient monitoring. This repository implements an end-to-end pipeline that bridges local clinical data (audio, vitals) to advanced Google Cloud medical models (MedASR, MedGemma).

## 🚀 Overview

- **MedASR Transcription**: Real-time conversion of doctor-patient dialogue into medical-grade transcripts.
- **MedGemma SOAP Integration**: Automated generation of clinical SOAP notes from encounter transcripts.
- **FHIR Vitals Streamer**: Simulation of real-time patient vitals (Heart Rate, BP) streaming to a centralized API.
- **MCP Server**: Integrated Model Context Protocol (MCP) server for tool-calling capabilities.

## 📂 Project Structure

```text
omnicare/
├── src/
│   ├── backend/               # Node.js Express Orchestrator & MCP Server
│   │   ├── omnicare-mcp.js    # Core server logic
│   │   ├── package.json
│   │   └── .env               # Configuration (Project IDs, Endpoints)
│   └── scripts/               # Python & Shell simulation clients
│       ├── test_audio.py      # ASR ➔ MedGemma E2E test client
│       ├── synthea_vitals.py  # FHIR observation streamer
│       └── convert_audio.ps1  # FFmpeg processing utility
├── data/                      # Sample audio and Synthea datasets
├── docs/                      # Generated results and walkthroughs
└── README.md
```

## 🛠️ Prerequisites

Before running the system, ensure you have the following installed:

1.  **Node.js (v18+)**
2.  **Python (3.9+)**
3.  **FFmpeg**: Required for audio normalization (16kHz mono).
    - Windows: `winget install -e --id Gyan.FFmpeg`
4.  **Google Cloud SDK**:
    - Run `gcloud auth application-default login` to authenticate.
5.  **Vertex AI APIs Enabled** in your Google Cloud Project.

## 🏁 Setup & Usage

### 1. Backend Setup
Navigate to the root and install dependencies:
```bash
npm install
```
Configure your `.env` file with your Vertex AI endpoint IDs:
```env
PROJECT_ID=your-project-id
LOCATION_ASR=europe-west1
ENDPOINT_ID_ASR=...
LOCATION_LLM=europe-west4
ENDPOINT_ID_LLM=...
```

### 2. Start the Orchestrator
```bash
node src/backend/omnicare-mcp.js
```

### 3. Run the Clinical Pipeline
To process an audio file and generate a SOAP note:
```powershell
# 1. Convert audio
./src/scripts/convert_audio.ps1

# 2. Run E2E pipeline
python src/scripts/test_audio.py
```

## 📝 Outputs
All generated transcription and SOAP notes are automatically saved to `docs/medgemma_output.md`.

---
*Built for Advanced Clinical Automation.*
