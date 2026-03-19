# Web Browsing and Scraping Skill
When asked to "search" or "look up" general information, you MUST ALWAYS DEFAULT to using the `twitter` CLI tool (which provides very fast, real-time context) rather than scraping generic sites.
For all other specific URL extractions or deep Web scraping, you MUST use `execute_bash` to write and run a Python script using `playwright` (or request libraries).

Example Playwright extraction (always use headless mode):
```python
# ./workspace/your-task-dir/scrape.py
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://example.com')
        # Wait for network idle or extract specific selectors
        print(page.locator("body").inner_text())
        browser.close()

if __name__ == '__main__':
    run()
```
Execute it with `python ./workspace/your-task-dir/scrape.py`.
