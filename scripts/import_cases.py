import os
import json
import glob
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: Missing Supabase credentials in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def import_cases():
    cases_dir = "data/cases"
    json_files = glob.glob(os.path.join(cases_dir, "*.json"))
    
    print(f"📂 Found {len(json_files)} case files in {cases_dir}")
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            filename = os.path.basename(file_path)
            print(f"Processing {filename}...")
            
            # Map JSON fields to DB Columns
            payload = {
                "case_number": case_data.get("case_number", "Unknown"),
                "case_type": case_data.get("case_type", "Unknown"),
                "court": case_data.get("court", "Unknown"),
                "status": case_data.get("status", "جاري"),
                
                # Flat fields
                "defendant_name": case_data.get("parties", {}).get("defendant", {}).get("full_name"),
                "charges": [c.get("charge") if isinstance(c, dict) else c for c in case_data.get("charges", [])],
                "facts": case_data.get("facts"),
                "notes": case_data.get("notes"),
                
                # JSONB fields
                "parties": case_data.get("parties"),
                "evidence": case_data.get("evidence"),
                "timeline": case_data.get("timeline"),
                "defense_strategy": case_data.get("defense_strategy"),
                
                "source_file": filename
            }
            
            # Insert
            res = supabase.table("cases").insert(payload).execute()
            print(f"✅ Imported: {payload['case_number']}")
            
        except Exception as e:
            print(f"❌ Failed to import {file_path}: {e}")

if __name__ == "__main__":
    print("--- QANOUNI Cases Importer ---")
    import_cases()
