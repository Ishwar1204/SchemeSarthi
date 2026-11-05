import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# --- CONFIGURATION ---
# The folder where PDFs will be saved
DOWNLOAD_FOLDER = "scheme_pdfs"

# List of URLs to scrape (Add more here!)
# Example: A generic government notification page (Replace with real targets)
TARGET_URLS = [
    "https://pmaymis.gov.in/",  # PMAY Guidelines Page
    # "https://nha.gov.in/PM-JAY",           # Ayushman Bharat
]

# Create the folder if it doesn't exist
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- HEADERS (Disguise as a Browser) ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def download_pdf(pdf_url, filename):
    """Downloads a single PDF"""
    try:
        response = requests.get(pdf_url, headers=HEADERS, stream=True)
        response.raise_for_status() # Check for errors
        
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed {filename}: {e}")
        return False

def crawl_website(url):
    """Finds all PDF links on a page and downloads them"""
    print(f"\n🕷️  Crawling: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links ('a' tags)
        links = soup.find_all('a', href=True)
        
        pdf_count = 0
        for link in links:
            href = link['href']
            
            # Check if it points to a PDF
            if href.lower().endswith('.pdf'):
                # Handle relative URLs (e.g., "/docs/guideline.pdf")
                full_url = urljoin(url, href)
                
                # Create a clean filename from the URL
                filename = href.split('/')[-1]
                
                # Download it
                download_pdf(full_url, filename)
                pdf_count += 1
                
                # Be polite! Wait 1 second so we don't crash their server
                time.sleep(1)
                
        print(f"📊 Summary: Found {pdf_count} PDFs on this page.")
        
    except Exception as e:
        print(f"🚨 Error crawling {url}: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("🚀 Starting Scheme Spider...")
    for target in TARGET_URLS:
        crawl_website(target)
    print("\n🎉 Scraping Complete! Check the 'scheme_pdfs' folder.")