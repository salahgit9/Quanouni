import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.database import get_supabase
from ingest_laws import ingest_laws
from ingest_jurisprudence import ingest_jurisprudence

def clean_database():
    print("--- 🧹 CLEANING DATABASE 🧹 ---")
    supabase = get_supabase()
    
    # Delete Laws
    print("Deleting existing Laws...")
    try:
        supabase.table("documents").delete().eq("category", "loi").execute()
        print(" > Laws deleted.")
    except Exception as e:
        print(f" > Error deleting laws: {e}")

    # Delete Jurisprudence
    print("Deleting existing Jurisprudence...")
    try:
        supabase.table("documents").delete().eq("category", "jurisprudence").execute()
        print(" > Jurisprudence deleted.")
    except Exception as e:
        print(f" > Error deleting jurisprudence: {e}")

    # Note: Chunks cascade delete automatically due to FK

def run_full_pipeline():
    # 1. Clean
    clean_database()
    
    # 2. Ingest Laws
    print("\n--- 📚 INGESTING LAWS (127 Files) 📚 ---")
    try:
        ingest_laws()
    except Exception as e:
        print(f"CRITICAL ERROR in Laws Ingestion: {e}")
        
    # 3. Ingest Jurisprudence
    print("\n--- ⚖️ INGESTING JURISPRUDENCE ⚖️ ---")
    try:
        ingest_jurisprudence()
    except Exception as e:
        print(f"CRITICAL ERROR in Jurisprudence Ingestion: {e}")
        
    print("\n--- ✅ FULL PIPELINE COMPLETE ✅ ---")

if __name__ == "__main__":
    run_full_pipeline()
