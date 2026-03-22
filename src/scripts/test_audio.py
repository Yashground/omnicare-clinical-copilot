import requests
import base64
import time
import json

# The backend URL
URL = "http://localhost:3000/api/transcribe"
# Path to the WAV file (16kHz mono int16)
AUDIO_FILE = r"..\..\data\test_audio.wav"

def test_transcription():
    print(f"Reading audio from {AUDIO_FILE}...")
    with open(AUDIO_FILE, "rb") as f:
        audio_data = f.read()
        
    encoded_audio = base64.b64encode(audio_data).decode("utf-8")
    # Generate a unique encounter ID for this specific run to avoid backend caching/merging
    encounter_id = f"enc_real_audio_{int(time.time())}"
    
    print(f"Sending audio to backend transcription API (Encounter: {encounter_id})...")
    payload = {
        "encounter_id": encounter_id,
        "text_chunk": "",
        "audio_chunk": encoded_audio
    }
    
    print(f"Sending request to {URL}...")
    try:
        start_time = time.time()
        response = requests.post(URL, json=payload)
        end_time = time.time()
        
        print(f"\nResponse Code: {response.status_code}")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        
        try:
            data = response.json()
            with open("medgemma_output.md", "w") as f:
                f.write("# OmniCare Output Log\n\n")
                f.write(f"**Response Code:** {response.status_code}\n")
                f.write(f"**Time Taken:** {end_time - start_time:.2f} seconds\n\n")
                
                f.write("## 1. MedASR Transcription\n")
                f.write(f"{data.get('current_transcript', 'N/A')}\n\n")
                
                f.write("## 2. MedGemma SOAP Note\n")
                f.write(f"{data.get('soap_note', 'No SOAP Note Generated')}\n")
                
            print("✅ Results successfully saved to medgemma_output.md")
        except Exception as json_e:
            print("Failed to parse JSON response:", json_e)
            print("\nResponse Body:")
            print(response.text)
        
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_transcription()
