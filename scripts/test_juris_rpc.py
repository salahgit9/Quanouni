import os
import requests
from dotenv import load_dotenv

load_dotenv('d:/TEST/QUANOUNI/new/.env')

url = os.getenv('VITE_SUPABASE_URL')
key = os.getenv('VITE_SUPABASE_ANON_KEY')

print(f'Supabase URL: {url}')
print(f'Key: {key[:15]}...')

# Dummy embedding (768 dims)
embedding = [0.01] * 768

rpc_url = f"{url}/rest/v1/rpc/match_documents"
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

# Test WITHOUT filter
print('\n--- Test 1: NO filter ---')
payload1 = {"query_embedding": embedding, "match_count": 3, "filter_category": None}
r1 = requests.post(rpc_url, headers=headers, json=payload1, timeout=30)
print(f'Status: {r1.status_code}')
if r1.status_code == 200:
    data = r1.json()
    print(f'Results: {len(data)} docs')
    if data:
        print(f'First doc category: {data[0].get("metadata", {}).get("category", "N/A")}')
else:
    print(f'Error: {r1.text[:300]}')

# Test WITH jurisprudence filter
print('\n--- Test 2: filter_category=jurisprudence ---')
payload2 = {"query_embedding": embedding, "match_count": 3, "filter_category": "jurisprudence"}
r2 = requests.post(rpc_url, headers=headers, json=payload2, timeout=30)
print(f'Status: {r2.status_code}')
if r2.status_code == 200:
    data = r2.json()
    print(f'Results: {len(data)} docs')
    if data:
        print(f'First doc category: {data[0].get("metadata", {}).get("category", "N/A")}')
    else:
        print('⚠️ NO JURISPRUDENCE DOCUMENTS FOUND!')
else:
    print(f'Error: {r2.text[:300]}')
