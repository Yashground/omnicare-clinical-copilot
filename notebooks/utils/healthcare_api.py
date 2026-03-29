"""
Google Cloud Healthcare API integration for OmniCare Clinical Copilot.

Provides FHIR store and DICOM store operations using the Healthcare API v1.
Replaces self-hosted HAPI FHIR / Orthanc with managed GCP services.

Prerequisites:
  - Enable the Cloud Healthcare API in your GCP project
  - Grant the service account (or user) the Healthcare FHIR/DICOM roles
  - pip install google-api-python-client google-auth
"""

import json
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Lazy API client
# ---------------------------------------------------------------------------
_healthcare_client = None
_credentials = None
_project_id = None
_location = None
_dataset_id = None


def _get_config():
    """Return (project_id, location, dataset_id) from env or Colab secrets."""
    global _project_id, _location, _dataset_id
    if _project_id:
        return _project_id, _location, _dataset_id

    _project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("PROJECT_ID")
    _location = os.environ.get("HEALTHCARE_LOCATION", "us-central1")
    _dataset_id = os.environ.get("HEALTHCARE_DATASET", "omnicare-dataset")

    try:
        from google.colab import userdata  # type: ignore
        _project_id = _project_id or userdata.get("GCP_PROJECT_ID")
    except Exception:
        pass

    if not _project_id:
        raise ValueError(
            "Set GCP_PROJECT_ID env var or Colab secret. "
            "Example: os.environ['GCP_PROJECT_ID'] = 'my-project-id'"
        )
    return _project_id, _location, _dataset_id


def _get_client():
    """Return a cached Healthcare API client."""
    global _healthcare_client, _credentials
    if _healthcare_client:
        return _healthcare_client

    try:
        from google.colab import auth  # type: ignore
        auth.authenticate_user()
    except ImportError:
        pass

    import google.auth  # type: ignore
    import google.auth.transport.requests  # type: ignore
    from googleapiclient import discovery  # type: ignore

    _credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-healthcare"]
    )
    _credentials.refresh(google.auth.transport.requests.Request())
    _healthcare_client = discovery.build("healthcare", "v1")
    return _healthcare_client


def _get_session():
    """Return an authorized requests.Session for direct FHIR REST calls."""
    import google.auth  # type: ignore
    import google.auth.transport.requests  # type: ignore
    from google.auth.transport.requests import AuthorizedSession  # type: ignore

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-healthcare"]
    )
    return AuthorizedSession(credentials)


# ===================================================================
# Dataset management
# ===================================================================

def _dataset_path():
    project, location, dataset = _get_config()
    return f"projects/{project}/locations/{location}/datasets/{dataset}"


def create_dataset():
    """Create the Healthcare dataset (idempotent — skips if exists)."""
    project, location, dataset = _get_config()
    client = _get_client()
    parent = f"projects/{project}/locations/{location}"
    try:
        client.projects().locations().datasets().create(
            parent=parent, body={}, datasetId=dataset
        ).execute()
        print(f"[Healthcare API] Created dataset: {dataset}")
    except Exception as e:
        if "ALREADY_EXISTS" in str(e) or "409" in str(e):
            print(f"[Healthcare API] Dataset already exists: {dataset}")
        else:
            raise
    return _dataset_path()


# ===================================================================
# FHIR Store
# ===================================================================

FHIR_STORE_ID = "omnicare-fhir"


def _fhir_store_path():
    return f"{_dataset_path()}/fhirStores/{FHIR_STORE_ID}"


def _fhir_base_url():
    project, location, dataset = _get_config()
    return (
        f"https://healthcare.googleapis.com/v1/"
        f"projects/{project}/locations/{location}/"
        f"datasets/{dataset}/fhirStores/{FHIR_STORE_ID}/fhir"
    )


def create_fhir_store():
    """Create the FHIR store (R4, idempotent)."""
    client = _get_client()
    try:
        client.projects().locations().datasets().fhirStores().create(
            parent=_dataset_path(),
            body={"version": "R4",
                  "enableUpdateCreate": True,
                  "disableReferentialIntegrity": True},
            fhirStoreId=FHIR_STORE_ID,
        ).execute()
        print(f"[FHIR] Created store: {FHIR_STORE_ID}")
    except Exception as e:
        if "ALREADY_EXISTS" in str(e) or "409" in str(e):
            print(f"[FHIR] Store already exists: {FHIR_STORE_ID}")
        else:
            raise
    return _fhir_store_path()


def upload_fhir_bundle(bundle: dict) -> dict:
    """Upload a FHIR Bundle (transaction or collection) to the FHIR store."""
    session = _get_session()

    # Convert collection bundles to transaction bundles for the API
    if bundle.get("type") == "collection":
        bundle = _collection_to_transaction(bundle)

    url = _fhir_base_url().rstrip("/fhir") + f"/fhirStores/{FHIR_STORE_ID}/fhir"
    # The correct endpoint for bundle upload
    base = _fhir_base_url()
    resp = session.post(
        base,
        json=bundle,
        headers={"Content-Type": "application/fhir+json"},
    )
    resp.raise_for_status()
    result = resp.json()
    entry_count = len(result.get("entry", []))
    print(f"[FHIR] Uploaded bundle: {entry_count} resources created/updated")
    return result


def upload_fhir_bundle_from_file(bundle_path: str) -> dict:
    """Upload a FHIR Bundle JSON file to the FHIR store."""
    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    return upload_fhir_bundle(bundle)


def _collection_to_transaction(bundle: dict) -> dict:
    """Convert a Synthea collection bundle to a transaction bundle."""
    tx_entries = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType", "")
        rid = resource.get("id", "")
        tx_entries.append({
            "resource": resource,
            "request": {
                "method": "PUT",
                "url": f"{rtype}/{rid}" if rid else rtype,
            },
        })
    return {"resourceType": "Bundle", "type": "transaction", "entry": tx_entries}


# --- FHIR Resource Queries ---

def query_fhir_resource(resource_type: str, params: dict = None) -> list:
    """Query FHIR resources from the store."""
    session = _get_session()
    url = f"{_fhir_base_url()}/{resource_type}"
    resp = session.get(url, params=params or {})
    resp.raise_for_status()
    bundle = resp.json()
    return [e["resource"] for e in bundle.get("entry", [])]


def get_patient(patient_id: str) -> Optional[dict]:
    """Get a specific Patient resource."""
    session = _get_session()
    url = f"{_fhir_base_url()}/Patient/{patient_id}"
    resp = session.get(url)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def query_vitals(patient_id: str) -> list:
    """Query vital-sign Observations for a patient."""
    return query_fhir_resource("Observation", {
        "patient": patient_id,
        "category": "vital-signs",
        "_count": "100",
        "_sort": "-date",
    })


def query_conditions(patient_id: str) -> list:
    """Query Conditions for a patient."""
    return query_fhir_resource("Condition", {
        "patient": patient_id,
        "_count": "100",
    })


def query_medications(patient_id: str) -> list:
    """Query MedicationRequests for a patient."""
    return query_fhir_resource("MedicationRequest", {
        "patient": patient_id,
        "_count": "100",
    })


def query_encounters(patient_id: str) -> list:
    """Query Encounters for a patient."""
    return query_fhir_resource("Encounter", {
        "patient": patient_id,
        "_count": "100",
    })


def create_fhir_resource(resource: dict) -> dict:
    """Create a single FHIR resource in the store."""
    session = _get_session()
    rtype = resource["resourceType"]
    url = f"{_fhir_base_url()}/{rtype}"
    resp = session.post(
        url, json=resource,
        headers={"Content-Type": "application/fhir+json"},
    )
    resp.raise_for_status()
    return resp.json()


def create_observation(patient_id: str, code: str, display: str,
                       value: float, unit: str,
                       effective_dt: str = "") -> dict:
    """Create a vital-sign Observation resource."""
    from datetime import datetime as dt
    resource = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                   "code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org",
                              "code": code, "display": display}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": effective_dt or dt.utcnow().isoformat() + "Z",
        "valueQuantity": {"value": value, "unit": unit,
                          "system": "http://unitsofmeasure.org"},
    }
    return create_fhir_resource(resource)


# ===================================================================
# DICOM Store
# ===================================================================

DICOM_STORE_ID = "omnicare-dicom"


def _dicom_store_path():
    return f"{_dataset_path()}/dicomStores/{DICOM_STORE_ID}"


def _dicom_base_url():
    project, location, dataset = _get_config()
    return (
        f"https://healthcare.googleapis.com/v1/"
        f"projects/{project}/locations/{location}/"
        f"datasets/{dataset}/dicomStores/{DICOM_STORE_ID}/dicomWeb"
    )


def create_dicom_store():
    """Create the DICOM store (idempotent)."""
    client = _get_client()
    try:
        client.projects().locations().datasets().dicomStores().create(
            parent=_dataset_path(),
            body={},
            dicomStoreId=DICOM_STORE_ID,
        ).execute()
        print(f"[DICOM] Created store: {DICOM_STORE_ID}")
    except Exception as e:
        if "ALREADY_EXISTS" in str(e) or "409" in str(e):
            print(f"[DICOM] Store already exists: {DICOM_STORE_ID}")
        else:
            raise
    return _dicom_store_path()


def upload_dicom_instance(dicom_path: str) -> dict:
    """Upload a DICOM file to the DICOM store via DICOMweb STOW-RS."""
    session = _get_session()
    url = f"{_dicom_base_url()}/studies"

    with open(dicom_path, "rb") as f:
        dicom_bytes = f.read()

    # DICOMweb STOW-RS uses multipart/related
    import email.mime.multipart
    import email.mime.base

    boundary = "boundary_dicom_upload"
    content_type = f'multipart/related; type="application/dicom"; boundary={boundary}'

    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/dicom\r\n\r\n"
    ).encode() + dicom_bytes + f"\r\n--{boundary}--".encode()

    resp = session.post(url, data=body, headers={"Content-Type": content_type})
    resp.raise_for_status()
    print(f"[DICOM] Uploaded: {os.path.basename(dicom_path)}")
    return resp.json() if resp.content else {"status": "uploaded"}


def list_dicom_studies() -> list:
    """List DICOM studies in the store."""
    session = _get_session()
    url = f"{_dicom_base_url()}/studies"
    resp = session.get(url, headers={"Accept": "application/dicom+json"})
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    return resp.json() if resp.content else []


def retrieve_dicom_instance(study_uid: str, series_uid: str,
                            instance_uid: str, output_path: str) -> str:
    """Retrieve a DICOM instance via DICOMweb WADO-RS."""
    session = _get_session()
    url = (f"{_dicom_base_url()}/studies/{study_uid}"
           f"/series/{series_uid}/instances/{instance_uid}")
    resp = session.get(url, headers={"Accept": "application/dicom"})
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)
    return output_path


# ===================================================================
# Setup helper — call once from Notebook 00
# ===================================================================

def setup_healthcare_stores():
    """Create dataset + FHIR store + DICOM store (idempotent)."""
    create_dataset()
    create_fhir_store()
    create_dicom_store()
    print("[Healthcare API] All stores ready.")
    return {
        "fhir_base_url": _fhir_base_url(),
        "dicom_base_url": _dicom_base_url(),
    }
