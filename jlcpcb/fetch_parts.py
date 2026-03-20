import pandas as pd
from playwright.sync_api import sync_playwright
import csv
import time
import datetime

def process_bom():
    print("Reading bom.xls...")
    df = pd.read_excel('bom.xls')
    
    if 'JLCPCB Part #' not in df.columns:
        print("Could not find 'JLCPCB Part #' column.")
        return

    part_to_comment = {}
    valid_parts = []
    for idx, row in df.dropna(subset=['JLCPCB Part #']).iterrows():
        p = str(row['JLCPCB Part #']).strip()
        if p.startswith('C') and p not in part_to_comment:
            valid_parts.append(p)
            part_to_comment[p] = str(row['Comment']) if pd.notna(row['Comment']) else ""
    
    print(f"Found {len(valid_parts)} unique valid parts to search.")
    
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(10000)
        
        # Only block images to ensure CSS loads properly
        def intercept_request(route):
            if route.request.resource_type in ["image", "media"]:
                route.abort()
            else:
                route.continue_()
        page.route("**/*", intercept_request)
        
        for idx, part in enumerate(valid_parts):
            print(f"[{idx+1}/{len(valid_parts)}] Fetching {part}...")
            url = f"https://jlcpcb.com/parts/componentSearch?searchTxt={part}"
            page.goto(url)
            
            try:
                # Wait for at least one table row that has our part.
                # If the part is invalid or not found, this might timeout.
                page.wait_for_selector('tr', timeout=10000)
                
                script = """
                (part) => {
                    let rows = document.querySelectorAll('tr');
                    for (let r of rows) {
                        let text = r.innerText;
                        // Be careful with matching just the part number, ensure it's precisely the part
                        if (text.includes(part)) {
                            let cells = r.querySelectorAll('td');
                            if (cells.length > 10) {
                                let stock = cells[8] ? cells[8].innerText.trim() : "N/A";
                                let priceText = cells[10] ? cells[10].innerText.trim().replace(/\\n/g, ' ') : "N/A";
                                
                                // Clean up stock (grab only digits just in case)
                                let stockNum = stock.replace(/\\D/g, '');
                                if (!stockNum) stockNum = '0';
                                
                                // Clean up price text - usually has format "1+ 1000+ $0.0439..."
                                // Let's just grab the first dollar amount
                                let priceMatch = priceText.match(/\\$[0-9\\.]+/);
                                let price = priceMatch ? priceMatch[0] : priceText;
                                
                                return {
                                    part: part,
                                    stock: parseInt(stockNum, 10),
                                    price: price
                                };
                            }
                        }
                    }
                    return null;
                }
                """
                
                data = page.evaluate(script, part)
                if data:
                    data['comment'] = part_to_comment[part]
                    print(f"  -> Comment: {data['comment'][:30]}, Stock: {data['stock']}, Price: {data['price']}")
                    results.append(data)
                else:
                    print(f"  -> Could not parse table for {part}.")
                    results.append({'part': part, 'comment': part_to_comment[part], 'stock': 0, 'price': "Not Found"})
                    
            except Exception as e:
                print(f"  -> Error or timeout waiting for {part}: {str(e)}")
                results.append({'part': part, 'comment': part_to_comment[part], 'stock': 0, 'price': "Error"})
                
        browser.close()
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"parts_results_{timestamp}.csv"
    print(f"\\nSaving results to {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['part', 'comment', 'stock', 'price'])
        writer.writeheader()
        writer.writerows(results)
    
    print("Done!")

if __name__ == "__main__":
    process_bom()
