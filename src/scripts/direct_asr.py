import os
import requests
import json
import base64
import subprocess

AUDIO_FILE = r"test_audio.wav"
PROJECT_ID = "32142846166"
ENDPOINT_ID = "mg-endpoint-d6a4a403-d834-4a85-ba9c-439648042ba0"
LOCATION = "europe-west1"
HOST = "mg-endpoint-d6a4a403-d834-4a85-ba9c-439648042ba0.europe-west1-779153331066.prediction.vertexai.goog"
URL = f"https://{HOST}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}:predict"

def get_token():
    with open("token.txt", "r") as f:
        return f.read().strip()

def test_asr():
    print("Reading audio...")
    with open(AUDIO_FILE, "rb") as f:
        audio_data = f.read()
    
    encoded_audio = base64.b64encode(audio_data).decode("utf-8")
    token = get_token()
    
    # Try the user's explicit format first (no instances array)
    # Wait, the URL has :predict which strongly requires {"instances": []}.
    # Let's try what the user pasted first:
    payload = {"file": encoded_audio}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("Sending payload...")
    resp = requests.post(URL, json=payload, headers=headers)
    print(f"Status: {resp.status_code}")
    with open("result_asr.json", "w") as out_f:
        out_f.write(resp.text)
    print("Response saved to result_asr.json")
        
if __name__ == "__main__":
    test_asr()
