import requests
import os
import time
import json
import urllib3
from urllib.parse import unquote
from bs4 import BeautifulSoup

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://conseildetat.dz/ar/%D8%A7%D9%84%D8%A5%D8%AC%D8%AA%D9%87%D8%A7%D8%AF-%D8%A7%D9%84%D9%82%D8%B6%D8%A7%D8%A6%D9%8A"
OUTPUT_DIR = r"d:\TEST\QUANOUNI\new\data\jurisprudence\conseil_etat"
METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape():
    page = 0
    all_metadata = []
    
    # Load existing metadata if resuming
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                all_metadata = json.load(f)
            print(f"Loaded {len(all_metadata)} existing records.")
        except:
            print("Could not load existing metadata, starting fresh.")

    existing_ids = {item['decision_number'] for item in all_metadata}

    chambers = ["chmbr_01", "chmbr_02", "chmbr_03", "chmbr_04", "chmbr_05"]
    
    for chamber_id in chambers:
        page = 0
        print(f"--- Processing Chamber: {chamber_id} ---")
        
        while True:
            print(f"Processing Page {page}...")
            
            params = {
                "field_numm_arr_value": "",
                "field_chamber_juris_value": chamber_id,
                "page": page
            }
            
            try:
                response = requests.get(BASE_URL, headers=headers, params=params, verify=False, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the results table
                table = soup.find('table', class_='cols-8')
                if not table:
                    print(f"No table found for {chamber_id} on page {page}. Moving to next chamber.")
                    break
                    
                rows = table.find('tbody').find_all('tr')
                if not rows:
                    print(f"No rows in table for {chamber_id}. Moving to next chamber.")
                    break
                    
                new_items_count = 0
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 8:
                        continue
                        
                    # Extract Data
                    decision_number = cols[0].get_text(strip=True)
                    chamber = cols[1].get_text(strip=True)
                    section = cols[2].get_text(strip=True)
                    date_str = cols[3].get_text(strip=True)
                    adaptation = cols[4].get_text(strip=True)
                    
                    # Subject (might be in ul/li)
                    subject = cols[5].get_text(separator=" | ", strip=True)
                    
                    principle = cols[6].get_text(separator="\n", strip=True)
                    
                    # PDF Link
                    pdf_link_tag = cols[7].find('a')
                    if not pdf_link_tag:
                        continue
                        
                    # Fix double encoded URLs (e.g. %2520 -> %20)
                    raw_url = pdf_link_tag['href']
                    pdf_url = unquote(raw_url)
                    
                    # Skip if already exists
                    if decision_number in existing_ids:
                        continue
                    
                    # Download PDF
                    try:
                        pdf_filename = f"{decision_number}.pdf"
                        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
                        
                        if not os.path.exists(pdf_path):
                            print(f"  Downloading Decision {decision_number}...")
                            # Handle spaces in URL if requests doesn't automatically (it usually does, but unquote helps)
                            pdf_resp = requests.get(pdf_url, headers=headers, verify=False, timeout=60)
                            pdf_resp.raise_for_status()
                            with open(pdf_path, "wb") as f:
                                f.write(pdf_resp.content)
                        else:
                            print(f"  Skipping {decision_number} (PDF exists)")
    
                        # Add to metadata
                        record = {
                            "decision_number": decision_number,
                            "chamber": chamber,
                            "section": section,
                            "date": date_str,
                            "adaptation": adaptation,
                            "subject": subject,
                            "principle": principle,
                            "pdf_url": pdf_url,
                            "local_path": pdf_path
                        }
                        all_metadata.append(record)
                        existing_ids.add(decision_number)
                        new_items_count += 1
                        
                    except Exception as e:
                        print(f"  Failed to download PDF for {decision_number} ({pdf_url}): {e}")
    
                print(f"  Page {page} done in {chamber_id}. Added {new_items_count} new decisions.")
                
                # Save metadata incrementally
                with open(METADATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_metadata, f, ensure_ascii=False, indent=2)
    
                # Check for "Next" button
                pager = soup.find('nav', class_='pager-nav')
                next_link = pager.find('a', rel='next') if pager else None
                
                if not next_link:
                    print(f"No 'Next' link found for {chamber_id}. Chamber complete.")
                    break
                    
                page += 1
                time.sleep(1) # Be polite
                
            except Exception as e:
                print(f"Error on chamber {chamber_id} page {page}: {e}")
                break

if __name__ == "__main__":
    scrape()
