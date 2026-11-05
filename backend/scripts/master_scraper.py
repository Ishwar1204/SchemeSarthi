import os
import json
from playwright.sync_api import sync_playwright
import time

# --- CONFIG ---
OUTPUT_DIR = "scheme_data"
BASE_URL = "https://www.myscheme.gov.in/search"

# Create folder
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def scrape_myscheme():
    with sync_playwright() as p:
        # 1. Launch Browser (Headless = False so you can see it working!)
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()
        
        print(f"🚀 Visiting {BASE_URL}...")
        page.goto(BASE_URL, timeout=60000)
        
        # 2. Handle the "Loading" state - Wait for scheme cards to appear
        # We wait for the specific grid class that holds schemes
        try:
            page.wait_for_selector('div.relative.flex.flex-col', timeout=10000)
        except:
            print("⚠️ Site took too long to load.")
        
        # 3. Scroll to load more (MyScheme uses infinite scroll)
        print("📜 Scrolling to load more schemes...")
        for _ in range(5): # Increase this number to get MORE schemes
            page.mouse.wheel(0, 5000)
            time.sleep(2) # Wait for new items to load
            
        # 4. Find all Scheme Cards
        # Note: These selectors depend on the website's structure. 
        # If they change, we update this line.
        scheme_links = page.query_selector_all('a[href^="/schemes/"]')
        
        print(f"🔍 Found {len(scheme_links)} schemes. Extracting data...")
        
        unique_urls = set()
        for link in scheme_links:
            href = link.get_attribute('href')
            full_url = f"https://www.myscheme.gov.in{href}"
            unique_urls.add(full_url)
            
        # 5. Visit Each Scheme Page and Extract Details
        for i, url in enumerate(unique_urls):
            if i >= 5: break # LIMIT to 5 for testing. Remove this later!
            
            print(f"   extracting: {url}")
            try:
                page.goto(url, timeout=30000)
                
                # Extract Title
                title = page.locator("h1").first.inner_text()
                
                # Extract The Main Content (Benefits, Eligibility, etc.)
                # This grabs all the text in the main tab section
                content = page.locator("div#benefits").inner_text() 
                
                # Save to File
                safe_title = "".join(x for x in title if x.isalnum() or x in " -_").strip()
                filename = f"{OUTPUT_DIR}/{safe_title}.txt"
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\n")
                    f.write(f"TITLE: {title}\n")
                    f.write("-" * 20 + "\n")
                    f.write(content)
                    
            except Exception as e:
                print(f"   ❌ Failed to scrape {url}: {e}")
                
        browser.close()
        print(f"✅ Done! Check the '{OUTPUT_DIR}' folder.")

if __name__ == "__main__":
    scrape_myscheme()