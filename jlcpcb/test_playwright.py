from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        part = "C2765186"
        url = f"https://jlcpcb.com/parts/componentSearch?searchTxt={part}"
        page.goto(url)
        page.wait_for_timeout(5000)
        
        script = """
        (part) => {
            let rows = document.querySelectorAll('tr');
            for (let r of rows) {
                if (r.innerText.includes(part)) {
                    let cells = r.querySelectorAll('td');
                    return Array.from(cells).map((c, i) => i + ": " + c.innerText.trim().replace(/\\n/g, ' '));
                }
            }
            return [];
        }
        """
        cells = page.evaluate(script, part)
        for c in cells:
            print(c)
        
        browser.close()

if __name__ == "__main__":
    run()
