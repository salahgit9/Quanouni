import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv('d:/TEST/QUANOUNI/new/.env')

url = os.getenv('VITE_SUPABASE_URL')
key = os.getenv('VITE_SUPABASE_ANON_KEY')

supabase = create_client(url, key)

print('Checking documents table for jurisprudence category...')

result = supabase.table('documents').select('id, category, filename').eq('category', 'jurisprudence').limit(5).execute()

if result.data:
    print(f'✅ Found {len(result.data)} jurisprudence documents:')
    for doc in result.data:
        print(f'  - {doc["filename"]} (ID: {doc["id"]})')
else:
    print('❌ NO JURISPRUDENCE DOCUMENTS FOUND!')
    print('\nChecking what categories exist...')
    all_docs = supabase.table('documents').select('category').execute()
    categories = set(d.get('category') for d in all_docs.data if d.get('category'))
    print(f'Available categories: {categories}')
