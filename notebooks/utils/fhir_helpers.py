"""
FHIR helper functions for OmniCare Clinical Copilot.
Handles parsing Synthea FHIR bundles and interacting with HAPI FHIR server.
"""

import json
import requests
from typing import Optional


def parse_fhir_bundle(bundle_path: str) -> dict:
    """Parse a Synthea FHIR Bundle JSON file and extract key resources."""
    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    if bundle.get("resourceType") != "Bundle":
        raise ValueError("File is not a valid FHIR Bundle.")

    entries = bundle.get("entry", [])
    resources = {"patients": [], "observations": [], "conditions": [],
                 "medications": [], "encounters": [], "allergies": [], "procedures": []}

    for entry in entries:
        res = entry.get("resource", {})
        rt = res.get("resourceType", "")
        if rt == "Patient":
            resources["patients"].append(res)
        elif rt == "Observation":
            resources["observations"].append(res)
        elif rt == "Condition":
            resources["conditions"].append(res)
        elif rt == "MedicationRequest":
            resources["medications"].append(res)
        elif rt == "Encounter":
            resources["encounters"].append(res)
        elif rt == "AllergyIntolerance":
            resources["allergies"].append(res)
        elif rt == "Procedure":
            resources["procedures"].append(res)

    return resources


def extract_vitals(observations: list) -> list:
    """Extract vital sign observations (those with valueQuantity or component)."""
    vitals = []
    for obs in observations:
        if "valueQuantity" in obs or "component" in obs:
            code_display = obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            code_value = obs.get("code", {}).get("coding", [{}])[0].get("code", "")
            timestamp = obs.get("effectiveDateTime", obs.get("issued", ""))

            if "valueQuantity" in obs:
                vitals.append({
                    "code": code_value,
                    "display": code_display,
                    "value": obs["valueQuantity"].get("value"),
                    "unit": obs["valueQuantity"].get("unit", ""),
                    "timestamp": timestamp
                })
            elif "component" in obs:
                # Blood pressure and similar multi-component vitals
                for comp in obs["component"]:
                    comp_display = comp.get("code", {}).get("coding", [{}])[0].get("display", "")
                    if "valueQuantity" in comp:
                        vitals.append({
                            "code": code_value,
                            "display": f"{code_display} - {comp_display}",
                            "value": comp["valueQuantity"].get("value"),
                            "unit": comp["valueQuantity"].get("unit", ""),
                            "timestamp": timestamp
                        })
    return vitals


def extract_conditions(conditions: list) -> list:
    """Extract active conditions from FHIR Condition resources."""
    result = []
    for cond in conditions:
        display = cond.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
        code = cond.get("code", {}).get("coding", [{}])[0].get("code", "")
        onset = cond.get("onsetDateTime", "")
        status = cond.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
        result.append({"display": display, "code": code, "onset": onset, "status": status})
    return result


def extract_medications(medications: list) -> list:
    """Extract medications from FHIR MedicationRequest resources."""
    result = []
    for med in medications:
        display = (med.get("medicationCodeableConcept", {})
                   .get("coding", [{}])[0].get("display", "Unknown"))
        status = med.get("status", "")
        result.append({"display": display, "status": status})
    return result


def extract_patient_demographics(patient: dict) -> dict:
    """Extract patient demographics from FHIR Patient resource."""
    name_parts = patient.get("name", [{}])[0]
    given = " ".join(name_parts.get("given", []))
    family = name_parts.get("family", "")
    return {
        "name": f"{given} {family}".strip(),
        "dob": patient.get("birthDate", ""),
        "gender": patient.get("gender", ""),
        "mrn": patient.get("id", ""),
        "address": _format_address(patient.get("address", [{}])[0]) if patient.get("address") else ""
    }


def _format_address(addr: dict) -> str:
    parts = addr.get("line", []) + [
        addr.get("city", ""), addr.get("state", ""), addr.get("postalCode", "")
    ]
    return ", ".join(p for p in parts if p)


def format_vitals_summary(vitals: list) -> str:
    """Format vitals list into a readable summary string."""
    if not vitals:
        return "No vitals recorded."
    lines = []
    for v in vitals:
        lines.append(f"- {v['display']}: {v['value']} {v['unit']} ({v['timestamp']})")
    return "\n".join(lines)


# --- HAPI FHIR Server Interaction ---

def upload_bundle_to_fhir(bundle_path: str, fhir_server_url: str) -> dict:
    """Upload a FHIR Bundle to a HAPI FHIR server."""
    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    response = requests.post(
        f"{fhir_server_url}/fhir",
        json=bundle,
        headers={"Content-Type": "application/fhir+json"}
    )
    response.raise_for_status()
    return response.json()


def query_fhir_vitals(patient_id: str, fhir_server_url: str) -> list:
    """Query vital sign observations from HAPI FHIR server."""
    response = requests.get(
        f"{fhir_server_url}/fhir/Observation",
        params={"patient": patient_id, "category": "vital-signs", "_count": "100"}
    )
    response.raise_for_status()
    bundle = response.json()
    observations = [e["resource"] for e in bundle.get("entry", [])]
    return extract_vitals(observations)


def query_fhir_conditions(patient_id: str, fhir_server_url: str) -> list:
    """Query conditions from HAPI FHIR server."""
    response = requests.get(
        f"{fhir_server_url}/fhir/Condition",
        params={"patient": patient_id, "_count": "100"}
    )
    response.raise_for_status()
    bundle = response.json()
    conditions = [e["resource"] for e in bundle.get("entry", [])]
    return extract_conditions(conditions)
