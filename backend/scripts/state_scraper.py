import os
import time
from playwright.sync_api import sync_playwright

# --- CONFIG ---
OUTPUT_DIR = "scheme_data_final" # New folder to avoid confusion
BASE_URL = "https://www.myscheme.gov.in/search/state/Maharashtra"
DOMAIN = "https://www.myscheme.gov.in"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def scrape_state_schemes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"🚀 Visiting {BASE_URL}...")
        page.goto(BASE_URL, timeout=60000)
        
        # --- PHASE 1: COLLECT URLs ---
        print("⏳ Waiting for scheme list...")
        try:
            page.wait_for_selector('a[href*="/schemes/"]', timeout=30000)
        except:
            print("⚠️ Timeout waiting for schemes.")
            browser.close()
            return

        all_scheme_urls = set()
        
        while True:
            links = page.query_selector_all('a[href*="/schemes/"]')
            count = 0
            for link in links:
                href = link.get_attribute('href')
                if href and "/schemes/" in href and len(href) > 5:
                    full_url = f"{DOMAIN}{href}" if href.startswith("/") else href
                    all_scheme_urls.add(full_url)
                    count += 1
            
            print(f"   📄 Found {count} schemes on this page.")

            # Pagination
            try:
                next_button = page.locator("ul.flex.list-none li:last-child button")
                if not next_button.is_visible() or next_button.is_disabled():
                    break
                next_button.click()
                time.sleep(2) 
            except:
                break

        print(f"📊 Total Unique Schemes: {len(all_scheme_urls)}")
        print("-" * 30)

        # --- PHASE 2: EXTRACT EVERYTHING ---
        for i, url in enumerate(all_scheme_urls):
            print(f"🕷️ ({i+1}/{len(all_scheme_urls)}) Scraping: {url}")
            
            try:
                page.goto(url, timeout=60000)
                
                # 1. SMART WAIT: Wait for 'Benefits' or 'Details' text to confirm load
                try:
                    page.wait_for_selector("text=Benefits", timeout=5000)
                except:
                    time.sleep(3) # Just wait blindly if specific text not found

                # 2. GET TITLE (Browser Tab Title is safest)
                page_title = page.title() # e.g., "Scheme Name - MyScheme"
                clean_title = page_title.split("-")[0].strip()
                
                # 3. CLICK TABS (To ensure hidden content loads)
                # We try to click typical tab names if they exist as buttons
                for tab_name in ["Eligibility", "Application Process", "Documents", "FaQ"]:
                    try:
                        # Look for button with exact text
                        page.get_by_role("button", name=tab_name).click(timeout=1000)
                    except:
                        pass # It's fine if the tab doesn't exist

                # 4. GRAB ALL TEXT (The Nuclear Option)
                # Instead of specific IDs, we grab the whole main container
                try:
                    # 'main' usually holds the body content
                    content = page.locator("main").inner_text()
                except:
                    # Fallback: Body text
                    content = page.locator("body").inner_text()

                # 5. SAVE
                url_slug = url.split("/")[-1]
                filename = f"{OUTPUT_DIR}/{url_slug}.txt"
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\n")
                    f.write(f"TITLE: {clean_title}\n")
                    f.write("-" * 20 + "\n")
                    f.write(content)
                    
            except Exception as e:
                print(f"   ❌ Failed: {e}")

        browser.close()
        print(f"\n🎉 Done! Check '{OUTPUT_DIR}' folder.")

if __name__ == "__main__":
    scrape_state_schemes()