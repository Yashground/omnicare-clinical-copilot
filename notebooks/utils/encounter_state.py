"""
Encounter state management for OmniCare Clinical Copilot.

Delegates to Firestore (firestore_db) when available, with automatic
fallback to local JSON files when Firestore is not configured.

This module preserves the original function signatures so existing
notebook code continues to work without changes.
"""

import json
import os
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Backend selection: Firestore or local JSON
# ---------------------------------------------------------------------------
_USE_FIRESTORE = None  # tri-state: None = not checked yet


def _check_firestore() -> bool:
    """Try to import and connect to Firestore. Cache the result."""
    global _USE_FIRESTORE
    if _USE_FIRESTORE is not None:
        return _USE_FIRESTORE
    try:
        from . import firestore_db  # noqa: F401
        firestore_db._get_db()  # verify connection
        _USE_FIRESTORE = True
        print("[encounter_state] Using Firestore backend")
    except Exception as e:
        _USE_FIRESTORE = False
        print(f"[encounter_state] Firestore unavailable ({e}), using local JSON")
    return _USE_FIRESTORE


# ---------------------------------------------------------------------------
# Local JSON fallback (original implementation)
# ---------------------------------------------------------------------------
ENCOUNTERS_DIR = "/content/encounters"


def _ensure_dir():
    os.makedirs(ENCOUNTERS_DIR, exist_ok=True)


def _local_save(encounter: dict) -> str:
    _ensure_dir()
    path = os.path.join(ENCOUNTERS_DIR, f"{encounter['encounter_id']}.json")
    with open(path, "w") as f:
        json.dump(encounter, f, indent=2, default=str)
    return path


def _local_load(encounter_id: str) -> dict:
    path = os.path.join(ENCOUNTERS_DIR, f"{encounter_id}.json")
    with open(path, "r") as f:
        return json.load(f)


def _local_list() -> list:
    _ensure_dir()
    return [f.replace(".json", "") for f in os.listdir(ENCOUNTERS_DIR)
            if f.endswith(".json") and not f.startswith(".")]


# ---------------------------------------------------------------------------
# Public API — delegates to Firestore or local JSON
# ---------------------------------------------------------------------------

def new_encounter_id() -> str:
    if _check_firestore():
        from .firestore_db import new_encounter_id as fs_new
        return fs_new()
    return f"enc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def blank_encounter(encounter_id: str, patient_name: str = "",
                    mrn: str = "", dob: str = "") -> dict:
    if _check_firestore():
        from .firestore_db import blank_encounter as fs_blank
        return fs_blank(encounter_id, patient_name=patient_name,
                        mrn=mrn, dob=dob)
    return {
        "encounter_id": encounter_id,
        "patient": {"name": patient_name, "mrn": mrn, "dob": dob},
        "stages": {
            "consultation": {
                "timestamp": None, "audio_file": None, "transcript": None,
                "soap_note": {"subjective": "", "objective": "",
                              "assessment": "", "plan": ""},
                "hear_findings": [],
            },
            "admission": {
                "timestamp": None, "fhir_patient_id": None,
                "vitals_history": [], "conditions": [],
                "medications": [], "admission_note": None,
            },
            "radiology": {
                "timestamp": None, "images": [], "reports": [],
            },
            "discharge": {
                "timestamp": None, "summary": None, "icd10_codes": [],
                "medications_at_discharge": [], "follow_up": None,
            },
        },
    }


def save_encounter(encounter: dict) -> str:
    if _check_firestore():
        from .firestore_db import save_encounter as fs_save
        return fs_save(encounter)
    return _local_save(encounter)


def load_encounter(encounter_id: str) -> dict:
    if _check_firestore():
        from .firestore_db import load_encounter as fs_load
        return fs_load(encounter_id)
    return _local_load(encounter_id)


def list_encounters() -> list:
    if _check_firestore():
        from .firestore_db import list_encounters as fs_list
        return fs_list()
    return _local_list()


def update_stage(encounter_id: str, stage: str, data: dict) -> dict:
    if _check_firestore():
        from .firestore_db import update_stage as fs_update
        return fs_update(encounter_id, stage, data)
    enc = _local_load(encounter_id)
    enc["stages"][stage].update(data)
    enc["stages"][stage]["timestamp"] = datetime.now().isoformat()
    _local_save(enc)
    return enc
