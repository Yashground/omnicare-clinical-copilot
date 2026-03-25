"""
Medical prompt templates for OmniCare Clinical Copilot.
Used across all notebooks for consistent MedGemma interactions.
"""

# Whisper initial_prompt for medical vocabulary priming
WHISPER_MEDICAL_PROMPT = (
    "Medical consultation transcript. "
    "Terminology: hypertension, diabetes mellitus, hyperlipidemia, "
    "metformin, lisinopril, atorvastatin, amoxicillin, prednisone, "
    "CBC, BMP, CMP, HbA1c, TSH, BNP, troponin, D-dimer, "
    "echocardiogram, electrocardiogram, CT scan, MRI, X-ray, "
    "dyspnea, tachycardia, bradycardia, edema, cyanosis, "
    "COPD, CHF, CAD, DVT, PE, UTI, GERD, "
    "mg, mcg, mL, mmHg, bpm, SpO2, BMI."
)

# SOAP note generation
SOAP_SYSTEM_PROMPT = (
    "You are an expert clinical AI assistant. Generate a structured SOAP "
    "(Subjective, Objective, Assessment, Plan) note based on the provided "
    "clinical encounter transcript. Be thorough and use proper medical terminology."
)

SOAP_USER_TEMPLATE = """Generate a structured SOAP note from this doctor-patient encounter transcript.

Transcript:
{transcript}

Format your response with these exact section headers:
**Subjective:**
**Objective:**
**Assessment:**
**Plan:**"""

# Admission note generation
ADMISSION_SYSTEM_PROMPT = (
    "You are a clinical documentation assistant specializing in hospital admission notes. "
    "Generate a comprehensive admission note based on the patient's clinical data."
)

ADMISSION_USER_TEMPLATE = """Generate a hospital admission note for this patient.

Patient Demographics:
{demographics}

Consultation SOAP Note:
{soap_note}

Current Vital Signs:
{vitals}

Active Conditions:
{conditions}

Current Medications:
{medications}

Allergies:
{allergies}

Format the admission note with these sections:
**Admitting Diagnosis:**
**History of Present Illness:**
**Past Medical History:**
**Current Medications:**
**Vital Signs on Admission:**
**Physical Examination:**
**Initial Assessment:**
**Admission Orders:**"""

# Radiology report generation
RADIOLOGY_SYSTEM_PROMPT = (
    "You are a radiologist assistant. Analyze the provided medical image in the "
    "context of the patient's clinical history. Provide a structured radiology report."
)

RADIOLOGY_USER_TEMPLATE = """Analyze this medical image and generate a structured radiology report.

Clinical Context:
{clinical_context}

Imaging Modality: {modality}
Body Part: {body_part}

Provide your report with these sections:
**Technique:**
**Findings:**
**Impression:**
**Recommendations:**"""

# Discharge summary generation
DISCHARGE_SYSTEM_PROMPT = (
    "You are a clinical documentation assistant specializing in discharge summaries. "
    "Generate a comprehensive discharge summary that covers the patient's entire hospital stay, "
    "from consultation through discharge."
)

DISCHARGE_USER_TEMPLATE = """Generate a comprehensive discharge summary for this patient.

=== CONSULTATION SOAP NOTE ===
{soap_note}

=== ADMISSION NOTE ===
{admission_note}

=== VITAL SIGNS TREND ===
{vitals_trend}

=== RADIOLOGY REPORTS ===
{radiology_reports}

Format the discharge summary with these sections:
**Patient Information:**
**Admission Date / Discharge Date:**
**Chief Complaint:**
**Hospital Course:**
**Key Findings (Labs, Imaging, Vitals):**
**Discharge Diagnoses:**
**Medications at Discharge:**
**Follow-up Instructions:**
**Patient Education:**"""
