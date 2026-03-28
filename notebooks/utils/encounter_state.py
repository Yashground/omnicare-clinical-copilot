"""
Encounter state management for OmniCare Clinical Copilot.
Stores and retrieves patient encounter data as JSON files.
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

ENCOUNTERS_DIR = "/content/encounters"


def _ensure_dir():
    os.makedirs(ENCOUNTERS_DIR, exist_ok=True)


def new_encounter_id() -> str:
    return f"enc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def blank_encounter(encounter_id: str, patient_name: str = "", mrn: str = "", dob: str = "") -> dict:
    return {
        "encounter_id": encounter_id,
        "patient": {"name": patient_name, "mrn": mrn, "dob": dob},
        "stages": {
            "consultation": {
                "timestamp": None,
                "audio_file": None,
                "transcript": None,
                "acoustic_biomarkers": None,
                "soap_note": {"subjective": "", "objective": "", "assessment": "", "plan": ""}
            },
            "admission": {
                "timestamp": None,
                "fhir_patient_id": None,
                "vitals_history": [],
                "conditions": [],
                "medications": [],
                "admission_note": None
            },
            "radiology": {
                "timestamp": None,
                "images": [],
                "reports": []
            },
            "discharge": {
                "timestamp": None,
                "summary": None,
                "icd10_codes": [],
                "medications_at_discharge": [],
                "follow_up": None
            }
        }
    }


def save_encounter(encounter: dict) -> str:
    _ensure_dir()
    path = os.path.join(ENCOUNTERS_DIR, f"{encounter['encounter_id']}.json")
    with open(path, "w") as f:
        json.dump(encounter, f, indent=2, default=str)
    return path


def load_encounter(encounter_id: str) -> dict:
    path = os.path.join(ENCOUNTERS_DIR, f"{encounter_id}.json")
    with open(path, "r") as f:
        return json.load(f)


def list_encounters() -> list:
    _ensure_dir()
    return [f.replace(".json", "") for f in os.listdir(ENCOUNTERS_DIR) if f.endswith(".json")]


def update_stage(encounter_id: str, stage: str, data: dict) -> dict:
    enc = load_encounter(encounter_id)
    enc["stages"][stage].update(data)
    enc["stages"][stage]["timestamp"] = datetime.now().isoformat()
    save_encounter(enc)
    return enc
