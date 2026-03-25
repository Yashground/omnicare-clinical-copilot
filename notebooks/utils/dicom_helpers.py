"""
DICOM helper functions for OmniCare Clinical Copilot.
Handles reading DICOM files and interacting with Orthanc DICOM server.
"""

import io
import requests
import numpy as np
from typing import Optional


def read_dicom_image(dicom_path: str):
    """Read a DICOM file and return pixel data as PIL Image + metadata."""
    import pydicom
    from PIL import Image

    ds = pydicom.dcmread(dicom_path)

    metadata = {
        "patient_name": str(getattr(ds, "PatientName", "Unknown")),
        "patient_id": str(getattr(ds, "PatientID", "")),
        "modality": str(getattr(ds, "Modality", "Unknown")),
        "body_part": str(getattr(ds, "BodyPartExamined", "Unknown")),
        "study_description": str(getattr(ds, "StudyDescription", "")),
        "series_description": str(getattr(ds, "SeriesDescription", "")),
        "study_date": str(getattr(ds, "StudyDate", "")),
        "institution": str(getattr(ds, "InstitutionName", "")),
        "rows": int(getattr(ds, "Rows", 0)),
        "columns": int(getattr(ds, "Columns", 0)),
    }

    # Convert pixel data to PIL Image
    pixel_array = ds.pixel_array.astype(float)

    # Normalize to 0-255
    pixel_array = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min() + 1e-8) * 255
    pixel_array = pixel_array.astype(np.uint8)

    # Handle different photometric interpretations
    if len(pixel_array.shape) == 2:
        image = Image.fromarray(pixel_array, mode="L").convert("RGB")
    elif len(pixel_array.shape) == 3:
        image = Image.fromarray(pixel_array).convert("RGB")
    else:
        raise ValueError(f"Unexpected pixel array shape: {pixel_array.shape}")

    return image, metadata


def download_sample_chest_xray(output_dir: str = "/content/sample_data") -> str:
    """Download a sample chest X-ray image for testing.
    Uses NIH ChestX-ray14 sample or a publicly available medical image.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    # Use a publicly available chest X-ray sample from the NIH dataset
    # This is a direct link to a sample image
    sample_url = "https://nihcc.app.box.com/shared/static/vfk49d74nhbxq3nqjg0900w5nvkorp5c.png"
    output_path = os.path.join(output_dir, "sample_chest_xray.png")

    if os.path.exists(output_path):
        print(f"Sample image already exists at {output_path}")
        return output_path

    print("Downloading sample chest X-ray image...")
    try:
        response = requests.get(sample_url, timeout=30)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"Saved to {output_path}")
    except Exception as e:
        print(f"Download failed: {e}")
        print("Generating a synthetic placeholder image instead...")
        from PIL import Image
        img = Image.new("L", (512, 512), color=128)
        img.save(output_path)
        print(f"Placeholder saved to {output_path}")

    return output_path


def load_medical_image(image_path: str):
    """Load a medical image from any supported format (DICOM, PNG, JPG)."""
    from PIL import Image

    if image_path.lower().endswith((".dcm", ".dicom")):
        return read_dicom_image(image_path)
    else:
        image = Image.open(image_path).convert("RGB")
        metadata = {
            "modality": "Unknown",
            "body_part": "Unknown",
            "study_description": "",
            "rows": image.height,
            "columns": image.width,
        }
        return image, metadata


# --- Orthanc DICOM Server Interaction ---

def upload_to_orthanc(dicom_path: str, orthanc_url: str) -> dict:
    """Upload a DICOM file to an Orthanc server."""
    with open(dicom_path, "rb") as f:
        response = requests.post(
            f"{orthanc_url}/instances",
            data=f.read(),
            headers={"Content-Type": "application/dicom"}
        )
    response.raise_for_status()
    return response.json()


def list_orthanc_studies(orthanc_url: str) -> list:
    """List all studies in the Orthanc server."""
    response = requests.get(f"{orthanc_url}/studies")
    response.raise_for_status()
    return response.json()


def get_orthanc_image(orthanc_url: str, instance_id: str):
    """Retrieve an image from Orthanc and return as PIL Image."""
    from PIL import Image

    response = requests.get(f"{orthanc_url}/instances/{instance_id}/preview")
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    return image
