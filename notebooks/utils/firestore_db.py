"""
Firestore-backed persistence for OmniCare Clinical Copilot.

Replaces JSON-file storage with Google Cloud Firestore.
Stores encounters, patients, vitals, medications, conditions
as queryable documents with subcollections.

Collections:
  patients/{patient_id}          — demographics
  encounters/{encounter_id}      — encounter metadata + stages
  encounters/{id}/vitals/{auto}  — individual vital readings
  encounters/{id}/medications/{auto} — medication records
  encounters/{id}/conditions/{auto}  — condition records
  encounters/{id}/agent_logs/{auto}  — agent activity audit trail
"""

import os
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Lazy Firestore client — initialised once on first call
# ---------------------------------------------------------------------------
_db = None
_PROJECT_ID = None


def _get_db():
    """Return (and cache) a Firestore client, authenticating in Colab if needed."""
    global _db, _PROJECT_ID
    if _db is not None:
        return _db

    try:
        from google.colab import auth  # type: ignore
        auth.authenticate_user()
    except ImportError:
        pass  # not in Colab — rely on ADC

    from google.cloud import firestore  # type: ignore

    # Try Colab secret, env var, or fall back to ADC project
    project = os.environ.get("GCP_PROJECT_ID") or os.environ.get("PROJECT_ID")
    if project is None:
        try:
            from google.colab import userdata  # type: ignore
            project = userdata.get("GCP_PROJECT_ID")
        except Exception:
            pass

    _db = firestore.Client(project=project)
    _PROJECT_ID = project or _db.project
    print(f"[Firestore] Connected to project: {_PROJECT_ID}")
    return _db


# ===================================================================
# Patient CRUD
# ===================================================================

def create_patient(patient_id: str, name: str, mrn: str, dob: str,
                   gender: str = "", address: str = "",
                   allergies: str = "NKDA") -> dict:
    """Create or overwrite a patient document."""
    db = _get_db()
    data = {
        "name": name,
        "mrn": mrn,
        "dob": dob,
        "gender": gender,
        "address": address,
        "allergies": allergies,
        "created_at": datetime.utcnow().isoformat(),
    }
    db.collection("patients").document(patient_id).set(data)
    return {"patient_id": patient_id, **data}


def get_patient(patient_id: str) -> Optional[dict]:
    """Retrieve a patient document."""
    doc = _get_db().collection("patients").document(patient_id).get()
    if doc.exists:
        return {"patient_id": doc.id, **doc.to_dict()}
    return None


def list_patients() -> list:
    """List all patient IDs."""
    return [doc.id for doc in _get_db().collection("patients").stream()]


# ===================================================================
# Encounter CRUD
# ===================================================================

def new_encounter_id() -> str:
    """Generate a unique encounter ID."""
    return f"enc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def blank_encounter(encounter_id: str, patient_id: str = "",
                    patient_name: str = "", mrn: str = "",
                    dob: str = "") -> dict:
    """Return a blank encounter structure (mirrors legacy JSON format)."""
    return {
        "encounter_id": encounter_id,
        "patient_id": patient_id,
        "patient": {"name": patient_name, "mrn": mrn, "dob": dob},
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "stages": {
            "consultation": {
                "timestamp": None,
                "audio_file": None,
                "transcript": None,
                "soap_note": {"subjective": "", "objective": "",
                              "assessment": "", "plan": ""},
                "hear_findings": [],
            },
            "admission": {
                "timestamp": None,
                "fhir_patient_id": None,
                "vitals_history": [],
                "conditions": [],
                "medications": [],
                "admission_note": None,
            },
            "radiology": {
                "timestamp": None,
                "images": [],
                "reports": [],
            },
            "discharge": {
                "timestamp": None,
                "summary": None,
                "icd10_codes": [],
                "medications_at_discharge": [],
                "follow_up": None,
            },
        },
    }


def save_encounter(encounter: dict) -> str:
    """Save an encounter document to Firestore."""
    db = _get_db()
    eid = encounter["encounter_id"]
    encounter["updated_at"] = datetime.utcnow().isoformat()
    db.collection("encounters").document(eid).set(encounter)
    return eid


def load_encounter(encounter_id: str) -> dict:
    """Load an encounter document from Firestore."""
    doc = _get_db().collection("encounters").document(encounter_id).get()
    if not doc.exists:
        raise FileNotFoundError(f"Encounter {encounter_id} not found in Firestore.")
    return doc.to_dict()


def list_encounters() -> list:
    """List all encounter IDs, ordered by creation time."""
    docs = (_get_db().collection("encounters")
            .order_by("created_at")
            .stream())
    return [doc.id for doc in docs]


def update_stage(encounter_id: str, stage: str, data: dict) -> dict:
    """Update a specific stage of an encounter."""
    enc = load_encounter(encounter_id)
    enc["stages"][stage].update(data)
    enc["stages"][stage]["timestamp"] = datetime.utcnow().isoformat()
    save_encounter(enc)
    return enc


def update_encounter_status(encounter_id: str, status: str) -> dict:
    """Update encounter status (active, admitted, discharged)."""
    enc = load_encounter(encounter_id)
    enc["status"] = status
    save_encounter(enc)
    return enc


# ===================================================================
# Vitals subcollection — queryable per encounter
# ===================================================================

def add_vital(encounter_id: str, code: str, display: str,
              value: float, unit: str, recorded_at: str = "") -> str:
    """Add a vital sign reading to the encounter subcollection."""
    db = _get_db()
    data = {
        "code": code,
        "display": display,
        "value": value,
        "unit": unit,
        "recorded_at": recorded_at or datetime.utcnow().isoformat(),
    }
    ref = (db.collection("encounters").document(encounter_id)
           .collection("vitals").add(data))
    return ref[1].id


def get_vitals(encounter_id: str) -> list:
    """Get all vitals for an encounter, ordered by time."""
    docs = (_get_db().collection("encounters").document(encounter_id)
            .collection("vitals").order_by("recorded_at").stream())
    return [{"vital_id": d.id, **d.to_dict()} for d in docs]


# ===================================================================
# Medications subcollection
# ===================================================================

def add_medication(encounter_id: str, display: str, status: str = "active",
                   dosage: str = "", prescribed_at: str = "") -> str:
    """Add a medication record to the encounter."""
    db = _get_db()
    data = {
        "display": display,
        "status": status,
        "dosage": dosage,
        "prescribed_at": prescribed_at or datetime.utcnow().isoformat(),
    }
    ref = (db.collection("encounters").document(encounter_id)
           .collection("medications").add(data))
    return ref[1].id


def get_medications(encounter_id: str, status: str = "") -> list:
    """Get medications for an encounter, optionally filtered by status."""
    query = (_get_db().collection("encounters").document(encounter_id)
             .collection("medications"))
    if status:
        query = query.where("status", "==", status)
    return [{"med_id": d.id, **d.to_dict()} for d in query.stream()]


def update_medication_status(encounter_id: str, med_id: str,
                             new_status: str) -> None:
    """Update medication status (active → discontinued, completed)."""
    (_get_db().collection("encounters").document(encounter_id)
     .collection("medications").document(med_id)
     .update({"status": new_status}))


# ===================================================================
# Conditions subcollection
# ===================================================================

def add_condition(encounter_id: str, display: str, code: str = "",
                  onset: str = "", status: str = "active") -> str:
    """Add a condition to the encounter."""
    db = _get_db()
    data = {
        "display": display,
        "code": code,
        "onset": onset,
        "status": status,
    }
    ref = (db.collection("encounters").document(encounter_id)
           .collection("conditions").add(data))
    return ref[1].id


def get_conditions(encounter_id: str, status: str = "") -> list:
    """Get conditions for an encounter."""
    query = (_get_db().collection("encounters").document(encounter_id)
             .collection("conditions"))
    if status:
        query = query.where("status", "==", status)
    return [{"condition_id": d.id, **d.to_dict()} for d in query.stream()]


# ===================================================================
# Agent logs subcollection — audit trail
# ===================================================================

def log_agent_action(encounter_id: str, agent_name: str,
                     action: str, details: str = "") -> str:
    """Log an agent action for audit/observability."""
    db = _get_db()
    data = {
        "agent": agent_name,
        "action": action,
        "details": details,
        "timestamp": datetime.utcnow().isoformat(),
    }
    ref = (db.collection("encounters").document(encounter_id)
           .collection("agent_logs").add(data))
    return ref[1].id


def get_agent_logs(encounter_id: str, agent_name: str = "") -> list:
    """Get agent logs for an encounter."""
    query = (_get_db().collection("encounters").document(encounter_id)
             .collection("agent_logs"))
    if agent_name:
        query = query.where("agent", "==", agent_name)
    docs = query.order_by("timestamp").stream()
    return [{"log_id": d.id, **d.to_dict()} for d in docs]
