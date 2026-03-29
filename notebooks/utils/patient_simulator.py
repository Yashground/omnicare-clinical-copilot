"""
Dynamic patient data generator for OmniCare Clinical Copilot.

Replaces hardcoded mock data with realistic, varied patient scenarios.
Can generate FHIR bundles, consultation transcripts, and patient profiles
either from templates or using MedGemma for creative generation.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Optional


# ===================================================================
# Scenario templates — diverse clinical presentations
# ===================================================================

SCENARIOS = [
    {
        "id": "pneumonia_diabetic",
        "chief_complaint": "Productive cough with fever for 3 days",
        "demographics": {
            "name": "John Smith", "gender": "male",
            "dob": "1965-03-15", "mrn": "MRN-2026-001",
        },
        "conditions": [
            {"display": "Type 2 diabetes mellitus", "code": "44054006", "onset": "2018-06-15"},
            {"display": "Essential hypertension", "code": "38341003", "onset": "2015-01-20"},
        ],
        "medications": [
            {"display": "Metformin 500mg", "dosage": "500mg BID", "status": "active"},
            {"display": "Lisinopril 10mg", "dosage": "10mg daily", "status": "active"},
        ],
        "vitals": {
            "temperature": (99.8, "degF"), "systolic": (138, "mmHg"),
            "diastolic": (82, "mmHg"), "heart_rate": (88, "bpm"),
            "respiratory_rate": (18, "breaths/min"), "spo2": (96, "%"),
        },
        "allergies": "NKDA",
        "transcript_seed": (
            "Patient is a 61-year-old male presenting with a 3-day history of "
            "productive cough with yellowish sputum, low-grade fever peaking at "
            "100.4°F, and fatigue. Past medical history significant for type 2 "
            "diabetes on metformin and hypertension on lisinopril. On examination, "
            "crackles heard in the right lower lobe. Plan: amoxicillin 500mg TID "
            "for 7 days, chest X-ray to rule out pneumonia, CBC and BMP."
        ),
    },
    {
        "id": "chest_pain_cardiac",
        "chief_complaint": "Chest pain radiating to left arm for 2 hours",
        "demographics": {
            "name": "Maria Garcia", "gender": "female",
            "dob": "1958-09-22", "mrn": "MRN-2026-002",
        },
        "conditions": [
            {"display": "Hyperlipidemia", "code": "55822004", "onset": "2016-03-10"},
            {"display": "Coronary artery disease", "code": "53741008", "onset": "2020-11-05"},
        ],
        "medications": [
            {"display": "Atorvastatin 40mg", "dosage": "40mg daily", "status": "active"},
            {"display": "Aspirin 81mg", "dosage": "81mg daily", "status": "active"},
            {"display": "Metoprolol 50mg", "dosage": "50mg BID", "status": "active"},
        ],
        "vitals": {
            "temperature": (98.6, "degF"), "systolic": (158, "mmHg"),
            "diastolic": (94, "mmHg"), "heart_rate": (102, "bpm"),
            "respiratory_rate": (22, "breaths/min"), "spo2": (94, "%"),
        },
        "allergies": "Penicillin — rash",
        "transcript_seed": (
            "Patient is a 67-year-old female with history of CAD and hyperlipidemia "
            "presenting with substernal chest pain radiating to left arm, onset 2 hours "
            "ago while climbing stairs. Pain is pressure-like, 7/10 severity. Associated "
            "with diaphoresis and mild dyspnea. No nausea or vomiting. Currently on "
            "atorvastatin, aspirin, and metoprolol. ECG shows ST depression in leads "
            "V4-V6. Troponin pending. Plan: serial troponins, cardiology consult, "
            "heparin drip, morphine PRN for pain."
        ),
    },
    {
        "id": "copd_exacerbation",
        "chief_complaint": "Worsening shortness of breath and wheezing for 5 days",
        "demographics": {
            "name": "Robert Chen", "gender": "male",
            "dob": "1952-07-08", "mrn": "MRN-2026-003",
        },
        "conditions": [
            {"display": "Chronic obstructive pulmonary disease", "code": "13645005", "onset": "2012-04-20"},
            {"display": "Essential hypertension", "code": "38341003", "onset": "2010-08-15"},
            {"display": "Gastroesophageal reflux disease", "code": "235595009", "onset": "2019-02-01"},
        ],
        "medications": [
            {"display": "Tiotropium 18mcg inhaler", "dosage": "18mcg daily", "status": "active"},
            {"display": "Albuterol inhaler", "dosage": "PRN", "status": "active"},
            {"display": "Amlodipine 5mg", "dosage": "5mg daily", "status": "active"},
            {"display": "Omeprazole 20mg", "dosage": "20mg daily", "status": "active"},
        ],
        "vitals": {
            "temperature": (100.2, "degF"), "systolic": (142, "mmHg"),
            "diastolic": (78, "mmHg"), "heart_rate": (96, "bpm"),
            "respiratory_rate": (24, "breaths/min"), "spo2": (89, "%"),
        },
        "allergies": "Sulfa drugs — anaphylaxis",
        "transcript_seed": (
            "Patient is a 73-year-old male with known COPD, presenting with 5-day "
            "worsening dyspnea, increased sputum production (greenish), and wheezing. "
            "Reports using albuterol every 2 hours without relief. 40-pack-year smoking "
            "history, quit 5 years ago. On exam, bilateral expiratory wheezes, prolonged "
            "expiration, accessory muscle use. SpO2 89% on room air. Plan: nebulized "
            "albuterol/ipratropium, prednisone 40mg x 5 days, azithromycin 250mg, "
            "supplemental O2 to target SpO2 90-92%, chest X-ray, ABG."
        ),
    },
    {
        "id": "uti_elderly",
        "chief_complaint": "Painful urination and lower abdominal pain for 2 days",
        "demographics": {
            "name": "Dorothy Williams", "gender": "female",
            "dob": "1948-12-03", "mrn": "MRN-2026-004",
        },
        "conditions": [
            {"display": "Type 2 diabetes mellitus", "code": "44054006", "onset": "2010-05-15"},
            {"display": "Osteoarthritis of knee", "code": "239873007", "onset": "2017-09-01"},
        ],
        "medications": [
            {"display": "Glipizide 5mg", "dosage": "5mg daily", "status": "active"},
            {"display": "Acetaminophen 500mg", "dosage": "500mg TID PRN", "status": "active"},
        ],
        "vitals": {
            "temperature": (101.2, "degF"), "systolic": (128, "mmHg"),
            "diastolic": (76, "mmHg"), "heart_rate": (92, "bpm"),
            "respiratory_rate": (16, "breaths/min"), "spo2": (98, "%"),
        },
        "allergies": "NKDA",
        "transcript_seed": (
            "Patient is a 77-year-old female with diabetes presenting with 2-day "
            "history of dysuria, urinary frequency, urgency, and suprapubic tenderness. "
            "Low-grade fever of 101.2. No flank pain or hematuria. History of recurrent "
            "UTIs, last episode 6 months ago. On exam, suprapubic tenderness to palpation, "
            "no CVA tenderness. UA shows positive leukocyte esterase and nitrites. Plan: "
            "nitrofurantoin 100mg BID x 5 days, urine culture, recheck if not improving "
            "in 48 hours. Counsel on adequate hydration."
        ),
    },
    {
        "id": "asthma_pediatric_adult",
        "chief_complaint": "Acute asthma exacerbation with persistent cough",
        "demographics": {
            "name": "Aisha Patel", "gender": "female",
            "dob": "1998-04-20", "mrn": "MRN-2026-005",
        },
        "conditions": [
            {"display": "Asthma, moderate persistent", "code": "195967001", "onset": "2008-03-10"},
            {"display": "Allergic rhinitis", "code": "61582004", "onset": "2010-06-01"},
        ],
        "medications": [
            {"display": "Fluticasone/salmeterol 250/50", "dosage": "1 puff BID", "status": "active"},
            {"display": "Montelukast 10mg", "dosage": "10mg daily", "status": "active"},
            {"display": "Albuterol inhaler", "dosage": "PRN", "status": "active"},
            {"display": "Cetirizine 10mg", "dosage": "10mg daily", "status": "active"},
        ],
        "vitals": {
            "temperature": (98.4, "degF"), "systolic": (118, "mmHg"),
            "diastolic": (72, "mmHg"), "heart_rate": (108, "bpm"),
            "respiratory_rate": (26, "breaths/min"), "spo2": (92, "%"),
        },
        "allergies": "Cats, dust mites, pollen",
        "transcript_seed": (
            "Patient is a 28-year-old female with moderate persistent asthma presenting "
            "with acute exacerbation triggered by a recent upper respiratory infection. "
            "Reports worsening cough, chest tightness, and wheezing for 3 days. Using "
            "albuterol every 3-4 hours with partial relief. Peak flow 60% of personal best. "
            "On exam, diffuse bilateral wheezes, no accessory muscle use at rest. SpO2 92% "
            "on room air. Plan: nebulized albuterol x3, prednisone 40mg x 5 days, "
            "continue maintenance inhaler, peak flow monitoring, follow-up in 1 week."
        ),
    },
]


# ===================================================================
# Scenario selection
# ===================================================================

def list_scenarios() -> list:
    """List available clinical scenarios with ID and chief complaint."""
    return [{"id": s["id"], "chief_complaint": s["chief_complaint"],
             "patient": s["demographics"]["name"]}
            for s in SCENARIOS]


def get_scenario(scenario_id: str = None) -> dict:
    """
    Get a scenario by ID, or return a random one.

    Args:
        scenario_id: Scenario ID string, or None for random selection.

    Returns:
        Full scenario dict.
    """
    if scenario_id:
        for s in SCENARIOS:
            if s["id"] == scenario_id:
                return s
        raise ValueError(f"Unknown scenario: {scenario_id}. "
                         f"Available: {[s['id'] for s in SCENARIOS]}")
    return random.choice(SCENARIOS)


# ===================================================================
# FHIR bundle generation from scenario
# ===================================================================

def generate_fhir_bundle(scenario: dict) -> dict:
    """
    Generate a complete FHIR R4 Bundle from a scenario template.

    Creates Patient, Observation (vitals), Condition, and MedicationRequest
    resources — no hardcoded JSON needed.
    """
    demo = scenario["demographics"]
    name_parts = demo["name"].split(" ", 1)
    given = name_parts[0]
    family = name_parts[1] if len(name_parts) > 1 else ""
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = []

    # Patient resource
    patient = {
        "resourceType": "Patient",
        "id": demo["mrn"],
        "name": [{"given": [given], "family": family}],
        "birthDate": demo["dob"],
        "gender": demo["gender"],
    }
    entries.append({"resource": patient})

    # Vital signs
    vitals_map = {
        "temperature": ("8310-5", "Body temperature"),
        "heart_rate": ("8867-4", "Heart rate"),
        "respiratory_rate": ("9279-1", "Respiratory rate"),
        "spo2": ("2708-6", "Oxygen saturation (SpO2)"),
    }

    for key, (loinc, display) in vitals_map.items():
        if key in scenario["vitals"]:
            val, unit = scenario["vitals"][key]
            obs = {
                "resourceType": "Observation",
                "status": "final",
                "category": [{"coding": [{"code": "vital-signs"}]}],
                "code": {"coding": [{"code": loinc, "display": display}]},
                "subject": {"reference": f"Patient/{demo['mrn']}"},
                "valueQuantity": {"value": val, "unit": unit},
                "effectiveDateTime": now,
            }
            entries.append({"resource": obs})

    # Blood pressure (compound observation)
    if "systolic" in scenario["vitals"] and "diastolic" in scenario["vitals"]:
        sys_val, sys_unit = scenario["vitals"]["systolic"]
        dia_val, dia_unit = scenario["vitals"]["diastolic"]
        bp = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"code": "vital-signs"}]}],
            "code": {"coding": [{"code": "85354-9", "display": "Blood pressure panel"}]},
            "subject": {"reference": f"Patient/{demo['mrn']}"},
            "component": [
                {"code": {"coding": [{"display": "Systolic"}]},
                 "valueQuantity": {"value": sys_val, "unit": sys_unit}},
                {"code": {"coding": [{"display": "Diastolic"}]},
                 "valueQuantity": {"value": dia_val, "unit": dia_unit}},
            ],
            "effectiveDateTime": now,
        }
        entries.append({"resource": bp})

    # Conditions
    for cond in scenario.get("conditions", []):
        c = {
            "resourceType": "Condition",
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "code": {"coding": [{"code": cond["code"], "display": cond["display"]}]},
            "subject": {"reference": f"Patient/{demo['mrn']}"},
            "onsetDateTime": cond.get("onset", ""),
        }
        entries.append({"resource": c})

    # Medications
    for med in scenario.get("medications", []):
        m = {
            "resourceType": "MedicationRequest",
            "status": med.get("status", "active"),
            "subject": {"reference": f"Patient/{demo['mrn']}"},
            "medicationCodeableConcept": {
                "coding": [{"display": med["display"]}]
            },
        }
        entries.append({"resource": m})

    # Allergy
    if scenario.get("allergies") and scenario["allergies"] != "NKDA":
        allergy = {
            "resourceType": "AllergyIntolerance",
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "type": "allergy",
            "code": {"text": scenario["allergies"]},
            "patient": {"reference": f"Patient/{demo['mrn']}"},
        }
        entries.append({"resource": allergy})

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries,
    }


# ===================================================================
# Dynamic transcript generation using MedGemma
# ===================================================================

def generate_dynamic_transcript(scenario: dict, model=None, processor=None,
                                max_new_tokens: int = 1024) -> str:
    """
    Generate a realistic consultation transcript from a scenario.

    If MedGemma model/processor are provided, uses the LLM to create
    a natural doctor-patient conversation. Otherwise, returns the
    scenario's transcript_seed.

    Args:
        scenario: A scenario dict from SCENARIOS.
        model: MedGemma model (optional).
        processor: MedGemma processor (optional).

    Returns:
        Consultation transcript string.
    """
    if model is None or processor is None:
        return scenario["transcript_seed"]

    import torch  # type: ignore

    demo = scenario["demographics"]
    conditions = ", ".join(c["display"] for c in scenario.get("conditions", []))
    medications = ", ".join(m["display"] for m in scenario.get("medications", []))
    vitals_str = ", ".join(
        f"{k}: {v[0]} {v[1]}" for k, v in scenario["vitals"].items()
    )

    messages = [
        {"role": "system", "content": (
            "You are a medical documentation AI. Generate a realistic, detailed "
            "doctor-patient consultation transcript based on the clinical scenario. "
            "Write it as a continuous narrative from the doctor's perspective, as if "
            "dictated during/after the encounter. Include history, examination findings, "
            "assessment, and plan. Use proper medical terminology."
        )},
        {"role": "user", "content": (
            f"Generate a consultation transcript for this patient:\n\n"
            f"Patient: {demo['name']}, {demo['gender']}, DOB {demo['dob']}\n"
            f"Chief Complaint: {scenario['chief_complaint']}\n"
            f"Known Conditions: {conditions}\n"
            f"Current Medications: {medications}\n"
            f"Allergies: {scenario.get('allergies', 'NKDA')}\n"
            f"Vitals: {vitals_str}\n\n"
            "Write a detailed, realistic consultation transcript."
        )},
    ]

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    transcript = processor.decode(new_tokens, skip_special_tokens=True).strip()

    # Fallback if generation is too short
    if len(transcript) < 100:
        return scenario["transcript_seed"]

    return transcript


# ===================================================================
# Vitals time-series generation
# ===================================================================

def generate_vitals_timeseries(scenario: dict, hours: int = 24,
                               interval_min: int = 60) -> list:
    """
    Generate a realistic vitals time-series based on the scenario's baseline.

    Creates multiple readings over time with physiologically plausible variation.

    Args:
        scenario: Scenario dict.
        hours: Number of hours to simulate.
        interval_min: Minutes between readings.

    Returns:
        List of vitals dicts with timestamps.
    """
    base_vitals = scenario["vitals"]
    readings = []
    base_time = datetime.utcnow() - timedelta(hours=hours)
    n_readings = (hours * 60) // interval_min

    # Variation ranges (as fraction of baseline)
    variation = {
        "temperature": 0.01,
        "systolic": 0.05, "diastolic": 0.05,
        "heart_rate": 0.08,
        "respiratory_rate": 0.10,
        "spo2": 0.02,
    }

    for i in range(n_readings):
        timestamp = (base_time + timedelta(minutes=i * interval_min)).isoformat() + "Z"
        reading = {"timestamp": timestamp}
        for key, (base_val, unit) in base_vitals.items():
            var = variation.get(key, 0.05)
            noise = random.gauss(0, base_val * var)
            # Clamp physiologically reasonable
            val = base_val + noise
            if key == "spo2":
                val = min(100, max(70, val))
            elif key == "heart_rate":
                val = max(40, val)
            elif key == "respiratory_rate":
                val = max(8, val)
            reading[key] = {"value": round(val, 1), "unit": unit}
        readings.append(reading)

    return readings
