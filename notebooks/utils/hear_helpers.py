"""
HeAR (Health Acoustic Representations) helpers for OmniCare Clinical Copilot.

Google's HeAR model produces 512-dim embeddings from 2-second audio clips,
trained on 300M+ clips of coughing, breathing, throat clearing, laughing,
and speaking. We use it to detect respiratory events during consultations.

Model: google/hear-pytorch
Input:  2-second clips at 16 kHz mono → shape (n, 32000)
Output: (n, 512) embedding vectors

References:
  - https://huggingface.co/google/hear-pytorch
  - https://github.com/Google-Health/hear
"""

import numpy as np
from typing import Optional

try:
    import torch  # type: ignore
except ImportError:
    pass


# ===================================================================
# Model loading
# ===================================================================

def load_hear_model(device: str = "cuda"):
    """
    Load the HeAR PyTorch model from Hugging Face.

    Returns:
        model: The HeAR model ready for inference.
    """
    from transformers import AutoModel  # type: ignore

    print("Loading HeAR (google/hear-pytorch)...")
    model = AutoModel.from_pretrained("google/hear-pytorch", trust_remote_code=True)
    model = model.to(device).eval()

    param_count = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"HeAR loaded on {device} ({param_count:.1f}M parameters)")
    return model


def load_hear_preprocessor():
    """
    Load the audio preprocessing function from the HeAR repo.

    The preprocessor converts raw audio waveforms to spectrograms
    that HeAR expects as input.

    Returns:
        preprocess_audio: Function that takes (n, 32000) tensor → spectrogram batch.
    """
    import importlib
    import subprocess
    import sys
    import os

    hear_repo = "/content/hear"
    if not os.path.exists(hear_repo):
        print("Cloning HeAR repo for audio preprocessing...")
        subprocess.run(
            ["git", "clone", "https://github.com/Google-Health/hear.git", hear_repo],
            check=True, capture_output=True,
        )

    if hear_repo not in sys.path:
        sys.path.insert(0, hear_repo)

    audio_utils = importlib.import_module("hear.python.data_processing.audio_utils")
    print("HeAR audio preprocessor loaded.")
    return audio_utils.preprocess_audio


# ===================================================================
# Audio segmentation
# ===================================================================

def segment_audio(audio_array: np.ndarray, sr: int = 16000,
                  clip_duration: float = 2.0,
                  overlap: float = 0.5) -> list:
    """
    Segment audio into fixed-length clips for HeAR.

    Args:
        audio_array: 1D numpy array of audio samples.
        sr: Sample rate (must be 16000 for HeAR).
        clip_duration: Duration of each clip in seconds (2.0 for HeAR).
        overlap: Overlap fraction between consecutive clips (0.0–0.9).

    Returns:
        List of dicts: [{"audio": np.array, "start_sec": float, "end_sec": float}, ...]
    """
    clip_samples = int(sr * clip_duration)
    hop_samples = int(clip_samples * (1.0 - overlap))

    if len(audio_array) < clip_samples:
        # Pad short audio to 2 seconds
        padded = np.zeros(clip_samples, dtype=np.float32)
        padded[:len(audio_array)] = audio_array
        return [{"audio": padded, "start_sec": 0.0, "end_sec": clip_duration}]

    clips = []
    for start in range(0, len(audio_array) - clip_samples + 1, hop_samples):
        end = start + clip_samples
        clip = audio_array[start:end].astype(np.float32)
        clips.append({
            "audio": clip,
            "start_sec": start / sr,
            "end_sec": end / sr,
        })

    return clips


# ===================================================================
# Embedding extraction
# ===================================================================

def get_hear_embeddings(clips: list, model, preprocess_fn,
                        device: str = "cuda") -> np.ndarray:
    """
    Get HeAR embeddings for a batch of audio clips.

    Args:
        clips: List of dicts from segment_audio().
        model: HeAR model from load_hear_model().
        preprocess_fn: Preprocessing function from load_hear_preprocessor().
        device: Torch device.

    Returns:
        np.ndarray of shape (n_clips, 512).
    """
    # Stack clips into a batch tensor: (n, 32000)
    raw_batch = torch.stack([
        torch.tensor(c["audio"], dtype=torch.float32) for c in clips
    ]).to(device)

    # Preprocess: raw audio → spectrograms
    spectrogram_batch = preprocess_fn(raw_batch)

    # Forward pass
    with torch.no_grad():
        output = model.forward(spectrogram_batch, return_dict=True,
                               output_hidden_states=True)

    # Extract the pooled embedding (CLS token or mean pooling)
    if hasattr(output, "pooler_output") and output.pooler_output is not None:
        embeddings = output.pooler_output
    elif hasattr(output, "last_hidden_state"):
        embeddings = output.last_hidden_state.mean(dim=1)
    else:
        embeddings = output[0].mean(dim=1)

    return embeddings.cpu().numpy()


# ===================================================================
# Respiratory event detection
# ===================================================================

# Reference embeddings for respiratory events.
# In production, these come from a fine-tuned classifier.
# For the MVP, we use cosine similarity with known cough embeddings
# obtained from a small calibration set.
_COUGH_CENTROID = None
_DETECTION_THRESHOLD = 0.65


def calibrate_cough_detector(cough_embeddings: np.ndarray,
                             threshold: float = 0.65):
    """
    Calibrate the cough detector with known cough embeddings.

    Args:
        cough_embeddings: (n, 512) embeddings from confirmed cough audio.
        threshold: Cosine similarity threshold for cough detection.
    """
    global _COUGH_CENTROID, _DETECTION_THRESHOLD
    _COUGH_CENTROID = cough_embeddings.mean(axis=0)
    _COUGH_CENTROID = _COUGH_CENTROID / np.linalg.norm(_COUGH_CENTROID)
    _DETECTION_THRESHOLD = threshold
    print(f"[HeAR] Cough detector calibrated with {len(cough_embeddings)} samples "
          f"(threshold={threshold:.2f})")


def detect_respiratory_events(embeddings: np.ndarray, clips: list,
                              threshold: float = None) -> list:
    """
    Detect cough and respiratory events from HeAR embeddings.

    Uses cosine similarity against a cough centroid. If no centroid
    is calibrated, falls back to embedding magnitude heuristics.

    Args:
        embeddings: (n, 512) HeAR embeddings.
        clips: Corresponding clip metadata from segment_audio().
        threshold: Override detection threshold.

    Returns:
        List of detected events:
        [{"start_sec": float, "end_sec": float, "event_type": str,
          "confidence": float}, ...]
    """
    thresh = threshold or _DETECTION_THRESHOLD
    events = []

    if _COUGH_CENTROID is not None:
        # Cosine similarity approach
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalised = embeddings / (norms + 1e-8)
        similarities = normalised @ _COUGH_CENTROID

        for i, sim in enumerate(similarities):
            if sim >= thresh:
                events.append({
                    "start_sec": clips[i]["start_sec"],
                    "end_sec": clips[i]["end_sec"],
                    "event_type": "cough",
                    "confidence": float(sim),
                })
    else:
        # Fallback: use embedding energy as a rough proxy
        # High-energy embeddings often correspond to non-speech events
        energies = np.linalg.norm(embeddings, axis=1)
        energy_mean = energies.mean()
        energy_std = energies.std()
        high_thresh = energy_mean + 1.5 * energy_std

        for i, energy in enumerate(energies):
            if energy > high_thresh:
                events.append({
                    "start_sec": clips[i]["start_sec"],
                    "end_sec": clips[i]["end_sec"],
                    "event_type": "respiratory_event",
                    "confidence": float(min(
                        (energy - energy_mean) / (energy_std + 1e-8) / 3.0, 1.0
                    )),
                })

    return events


# ===================================================================
# High-level analysis function (used by HeARAgent)
# ===================================================================

def analyze_audio_for_respiratory_events(
    audio_path: str,
    model,
    preprocess_fn,
    device: str = "cuda",
    overlap: float = 0.5,
    threshold: float = None,
) -> dict:
    """
    Full pipeline: audio file → HeAR embeddings → respiratory event detection.

    Args:
        audio_path: Path to a WAV/MP3 audio file.
        model: HeAR model.
        preprocess_fn: HeAR audio preprocessor.
        device: Torch device.
        overlap: Clip overlap fraction.
        threshold: Detection threshold.

    Returns:
        {
            "events": [...],
            "total_clips": int,
            "audio_duration_sec": float,
            "summary": str,
        }
    """
    import librosa  # type: ignore

    # Load audio at 16 kHz mono
    audio, sr = librosa.load(audio_path, sr=16000, mono=True)
    duration = len(audio) / sr

    # Segment into 2-second clips
    clips = segment_audio(audio, sr=16000, clip_duration=2.0, overlap=overlap)

    if not clips:
        return {
            "events": [],
            "total_clips": 0,
            "audio_duration_sec": duration,
            "summary": "Audio too short for analysis.",
        }

    # Get HeAR embeddings
    embeddings = get_hear_embeddings(clips, model, preprocess_fn, device)

    # Detect events
    events = detect_respiratory_events(embeddings, clips, threshold)

    # Build summary
    if events:
        event_types = {}
        for e in events:
            et = e["event_type"]
            event_types[et] = event_types.get(et, 0) + 1

        parts = [f"{count} {etype}(s)" for etype, count in event_types.items()]
        summary = (
            f"Detected {len(events)} respiratory event(s) in "
            f"{duration:.1f}s audio: {', '.join(parts)}. "
            f"Timestamps: {', '.join(f'{e['start_sec']:.1f}s' for e in events[:5])}"
        )
    else:
        summary = f"No respiratory events detected in {duration:.1f}s audio."

    return {
        "events": events,
        "total_clips": len(clips),
        "audio_duration_sec": duration,
        "summary": summary,
    }


def generate_clinical_suggestion(events: list, transcript: str,
                                 model, processor,
                                 max_new_tokens: int = 512) -> str:
    """
    Use MedGemma to interpret HeAR findings in clinical context.

    Args:
        events: Detected respiratory events from HeAR.
        transcript: Consultation transcript for context.
        model: MedGemma model.
        processor: MedGemma processor.

    Returns:
        Clinical suggestion string.
    """
    if not events:
        return ""

    event_desc = "\n".join(
        f"- {e['event_type']} at {e['start_sec']:.1f}–{e['end_sec']:.1f}s "
        f"(confidence: {e['confidence']:.0%})"
        for e in events
    )

    messages = [
        {"role": "system", "content": (
            "You are a clinical AI assistant. The HeAR acoustic model has detected "
            "respiratory events during a patient consultation. Analyse these findings "
            "alongside the consultation transcript and provide brief clinical suggestions."
        )},
        {"role": "user", "content": (
            f"HeAR Acoustic Analysis Findings:\n{event_desc}\n\n"
            f"Consultation Transcript:\n{transcript[:1000]}\n\n"
            "Based on the acoustic findings and clinical context, provide:\n"
            "1. Clinical significance of detected events\n"
            "2. Recommended follow-up actions\n"
            "3. Any conditions to consider"
        )},
    ]

    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True,
        return_dict=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    return processor.decode(new_tokens, skip_special_tokens=True).strip()
