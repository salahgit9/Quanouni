import os
from dotenv import load_dotenv
import requests

load_dotenv('d:/TEST/QUANOUNI/new/.env')

groq_key = os.getenv('GROQ_API_KEY')
print(f'GROQ API Key: {groq_key[:15] if groq_key else "MISSING"}...')

headers = {
    "Authorization": f"Bearer {groq_key}",
    "Content-Type": "application/json"
}

data = {
    "messages": [{"role": "user", "content": "قل مرحبا"}],
    "model": "llama-3.3-70b-versatile",
    "max_tokens": 50
}

try:
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                     headers=headers, json=data, timeout=30)
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        content = r.json()['choices'][0]['message']['content']
        print(f'SUCCESS! Response: {content}')
    else:
        print(f'Error: {r.text[:300]}')
except Exception as e:
    print(f'Exception: {e}')
