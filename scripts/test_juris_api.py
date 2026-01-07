import requests

API_URL = "http://127.0.0.1:8000/api"

# Login
auth = requests.post(f"{API_URL}/login", json={"username": "salah", "password": "password123"})
if not auth.ok:
    print(f"Login failed: {auth.text}")
    exit()
token = auth.json()['token']
headers = {"Authorization": f"Bearer {token}"}

# Test Jurisprudence
print("Testing Jurisprudence endpoint...")
payload = {
    "legal_issue": "ما هي شروط بطلان الاعتراف المنتزع بالإكراه؟",
    "chamber": None,
    "top_k": 5
}

resp = requests.post(f"{API_URL}/legal/jurisprudence", json=payload, headers=headers, timeout=120)

print(f"Status: {resp.status_code}")
if resp.ok:
    data = resp.json()
    print(f"Analysis: {data.get('analysis', 'N/A')[:200]}")
    print(f"Sources: {len(data.get('sources', []))}")
else:
    print(f"Error: {resp.text}")
