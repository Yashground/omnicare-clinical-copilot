import time
import requests
import sys

BACKEND_URL = "http://localhost:3000/api/transcribe"

def stream_mock_encounter():
    """
    Mocks a doctor-patient encounter by sending transcript chunks
    to the Unified Backend API every few seconds.
    """
    encounter_id = f"enc_{int(time.time())}"
    
    mock_chunks = [
        "Patient presents with a 3-day history of productive cough.",
        " Patient also reports low-grade fever and fatigue.",
        " No known allergies.",
        " I will prescribe amoxicillin 500mg three times daily.",
        " Patient advised to return if symptoms worsen."
    ]
    
    print(f"Starting mock medical encounter (ID: {encounter_id})...\n")
    
    for i, chunk in enumerate(mock_chunks):
        print(f"Sending chunk {i+1}: '{chunk}'")
        try:
            # Send chunk to the unified API
            resp = requests.post(BACKEND_URL, json={
                "encounter_id": encounter_id,
                "text_chunk": chunk,
            })
            
            if resp.status_code == 200:
                print(f"✅ Backend received chunk.")
                # The backend might return an updated SOAP note if triggered
                data = resp.json()
                if "soap_note" in data and data["soap_note"]:
                    print("\n--- UPDATED SOAP NOTE ---")
                    print(data["soap_note"])
                    print("-------------------------\n")
            else:
                print(f"❌ Error: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            print(f"❌ Connection error (is backend running?): {e}")
            break
            
        time.sleep(3) # Mock the time it takes to speak the next chunk
        
    print(f"\nEncounter {encounter_id} complete.")

if __name__ == "__main__":
    stream_mock_encounter()
