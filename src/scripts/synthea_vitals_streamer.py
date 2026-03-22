import sys
import json
import time
import requests

API_URL = "http://localhost:3000/api/fhir/observation"

def stream_vitals(fhir_bundle_path):
    print(f"Loading Synthea FHIR Bundle: {fhir_bundle_path}")
    
    try:
        with open(fhir_bundle_path, 'r', encoding='utf-8') as f:
            bundle = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found - {fhir_bundle_path}")
        sys.exit(1)

    if bundle.get("resourceType") != "Bundle":
        print("Error: File is not a valid FHIR Bundle.")
        sys.exit(1)

    # Extract all Observations
    observations = [
        entry["resource"] for entry in bundle.get("entry", [])
        if entry.get("resource", {}).get("resourceType") == "Observation"
    ]

    print(f"Found {len(observations)} Observation records.")
    print("Starting vital sign stream. Press Ctrl+C to stop...\n")

    for obs in observations:
        code_display = obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown Observation")
        
        # We only want to stream actual vitals (e.g., Blood Pressure, Heart rate, Respiratory rate)
        # For simulation purposes, we'll stream anything that has a valueQuantity or component values
        if "valueQuantity" in obs or "component" in obs:
            try:
                response = requests.post(API_URL, json=obs)
                if response.status_code == 200:
                    print(f"✅ Streamed: {code_display}")
                else:
                    print(f"❌ Failed to stream: {code_display} (Status: {response.status_code})")
            except requests.exceptions.ConnectionError:
                print("❌ Connection Error: Is the Node.js backend running on port 3000?")
                sys.exit(1)
            
            # Simulate real-time delay between monitor readings
            time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python synthea_vitals_streamer.py <path_to_synthea_patient.json>")
        sys.exit(1)
    
    stream_vitals(sys.argv[1])
