
import requests
import json

url = "http://127.0.0.1:8001/ask"
payload = {
    "question": "What is PMAY?",
    "language": "English"
}

print(f"Sending request to {url}...")
try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
