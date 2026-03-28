"""
MCP tool definitions for OmniCare Clinical Copilot.
These functions wrap the model inference + API calls and can be exposed
as MCP tools via the Python MCP SDK.
"""

from typing import Optional
import os
import json
import numpy as np
import tensorflow as tf
import librosa
from huggingface_hub import snapshot_download
from .prompts import SOAP_USER_TEMPLATE

try:
    import torch  # type: ignore
except ImportError:
    pass

try:
    from .prompts import (  # type: ignore
        SOAP_SYSTEM_PROMPT, SOAP_USER_TEMPLATE,
        ADMISSION_SYSTEM_PROMPT, ADMISSION_USER_TEMPLATE,
        RADIOLOGY_SYSTEM_PROMPT, RADIOLOGY_USER_TEMPLATE,
        DISCHARGE_SYSTEM_PROMPT, DISCHARGE_USER_TEMPLATE
    )
except ImportError:
    pass


# ============================================================
# Tool: transcribe_audio
# ============================================================
def transcribe_audio(audio_path: str, asr_pipeline, medical_prompt: str) -> str:
    """Transcribe audio using Whisper with medical vocabulary prompting."""
    result = asr_pipeline(
        audio_path,
        generate_kwargs={"initial_prompt": medical_prompt},
        return_timestamps=False
    )
    return result["text"].strip()


# ============================================================
# HeAR Acoustic Biomarker Analysis
# ============================================================
_HEAR_MODEL = None

def load_hear_model():
    """Loads the Google HeAR event detector into memory."""
    global _HEAR_MODEL
    if _HEAR_MODEL is None:
        print("Loading Google HeAR Event Detector...")
        repo_path = snapshot_download(repo_id="google/hear")
        model_path = os.path.join(repo_path, 'event_detector', 'event_detector_large')
        _HEAR_MODEL = tf.keras.layers.TFSMLayer(model_path, call_endpoint='serving_default')
    return _HEAR_MODEL

def detect_acoustic_symptoms(audio_file: str) -> dict:
    """Detect acoustic biomarkers using Google HeAR."""
    model = load_hear_model()
    audio_array, sr = librosa.load(audio_file, sr=16000, mono=True)
    
    chunk_size = 32000
    cough_count = 0
    highest_confidence = 0.0
    
    for i in range(0, len(audio_array), chunk_size):
        chunk = audio_array[i:i + chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            
        input_tensor = tf.expand_dims(tf.constant(chunk, dtype=tf.float32), axis=0)
        predictions = model(input_tensor)
        output_tensor = predictions['mobilenetv3_large_model'][0]
        
        cough_prob = float(output_tensor[0])
        if cough_prob > 0.50:
            cough_count += 1
            highest_confidence = max(highest_confidence, cough_prob)
                
    return {
        "symptoms_detected": "Cough" if cough_count > 0 else "None",
        "total_cough_events": cough_count,
        "max_confidence_score": f"{highest_confidence * 100:.1f}%",
        "clinical_note": f"Acoustic AI detected {cough_count} coughing events during the consultation." if cough_count > 0 else "No prominent respiratory symptoms detected acoustically."
    }


# ============================================================
# Tool: generate_soap_note
# ============================================================
def generate_soap_note(transcript: str, model, processor, max_new_tokens: int = 1024, acoustic_biomarkers: dict = None) -> str:
    """Generate a SOAP note from a transcript using MedGemma."""

    if acoustic_biomarkers:
        acoustic_str = json.dumps(acoustic_biomarkers, indent=2)
    else:
        acoustic_str = "No acoustic data captured for this encounter."

    prompt = SOAP_USER_TEMPLATE.format(
        transcript=transcript,
        acoustic_data=acoustic_str
    )

    messages = [
        {"role": "system", "content": SOAP_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    # Decode only the new tokens
    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    return processor.decode(new_tokens, skip_special_tokens=True).strip()


# ============================================================
# Tool: generate_admission_note
# ============================================================
def generate_admission_note(
    demographics: str, soap_note: str, vitals: str,
    conditions: str, medications: str, allergies: str,
    model, processor, max_new_tokens: int = 1024
) -> str:
    """Generate an admission note using MedGemma."""

    messages = [
        {"role": "system", "content": ADMISSION_SYSTEM_PROMPT},
        {"role": "user", "content": ADMISSION_USER_TEMPLATE.format(
            demographics=demographics, soap_note=soap_note, vitals=vitals,
            conditions=conditions, medications=medications, allergies=allergies
        )}
    ]

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    return processor.decode(new_tokens, skip_special_tokens=True).strip()


# ============================================================
# Tool: analyze_medical_image
# ============================================================
def analyze_medical_image(
    image, clinical_context: str, modality: str, body_part: str,
    model, processor, max_new_tokens: int = 1024
) -> str:
    """Analyze a medical image using MedGemma multimodal."""

    user_content = RADIOLOGY_USER_TEMPLATE.format(
        clinical_context=clinical_context, modality=modality, body_part=body_part
    )

    messages = [
        {"role": "system", "content": RADIOLOGY_SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": user_content}
        ]}
    ]

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    return processor.decode(new_tokens, skip_special_tokens=True).strip()


# ============================================================
# Tool: generate_discharge_summary
# ============================================================
def generate_discharge_summary(
    soap_note: str, admission_note: str, vitals_trend: str, radiology_reports: str,
    model, processor, max_new_tokens: int = 1536
) -> str:
    """Generate a comprehensive discharge summary using MedGemma."""

    messages = [
        {"role": "system", "content": DISCHARGE_SYSTEM_PROMPT},
        {"role": "user", "content": DISCHARGE_USER_TEMPLATE.format(
            soap_note=soap_note, admission_note=admission_note,
            vitals_trend=vitals_trend, radiology_reports=radiology_reports
        )}
    ]

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    return processor.decode(new_tokens, skip_special_tokens=True).strip()


# ============================================================
# Tool: parse_soap_sections
# ============================================================
def parse_soap_sections(soap_text: str) -> dict:
    """Parse a SOAP note text into structured sections."""
    sections = {"subjective": "", "objective": "", "assessment": "", "plan": ""}
    current_section = ""

    for line in soap_text.split("\n"):
        line_lower = line.lower().strip()
        if "subjective" in line_lower and ("**" in line or ":" in line):
            current_section = "subjective"
            continue
        elif "objective" in line_lower and ("**" in line or ":" in line):
            current_section = "objective"
            continue
        elif "assessment" in line_lower and ("**" in line or ":" in line):
            current_section = "assessment"
            continue
        elif "plan" in line_lower and ("**" in line or ":" in line):
            current_section = "plan"
            continue

        if current_section:
            sections[current_section] += line + "\n"

    # Strip trailing whitespace from each section
    for key in sections:
        sections[key] = sections[key].strip()

    return sections
