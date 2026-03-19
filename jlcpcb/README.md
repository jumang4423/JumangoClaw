# JLCPCB BOM Price & Stock Tracker

This project automates the extraction of pricing and stock data for LCSC/JLCPCB parts directly from the JLCPCB Parts library using Playwright. It also generates a multi-page PDF report visualizing the historical price and stock trends for each part across multiple script runs.

## Prerequisites

You'll need Python 3 installed. It is recommended to use the `--break-system-packages` flag or a virtual environment.

### Setup

Install the required Python packages:
```bash
pip3 install --break-system-packages pandas xlrd playwright matplotlib openpyxl
```

Install Playwright browsers:
```bash
playwright install chromium
```

## How to Run

### 1. Fetch Parts Data
Ensure you have a `bom.xls` file in the same directory containing a `JLCPCB Part #` column and a `Comment` column.

Run the scraper to fetch the newest data:
```bash
python3 fetch_parts.py
```
This will open a headless Chrome browser, search JLCPCB for each part, and output a new file named `parts_results_YYYYMMDD_HHMMSS.csv` containing the snapshot of current prices and stock. 

### 2. Generate PDF Report
Once you have run the scraper one or more times, you can generate a visual historical report.

Run the report generator:
```bash
python3 generate_report.py
```
This script reads all `parts_results_*.csv` files in the directory, parses the dates from the filenames, and compiles them. It outputs a `parts_report.pdf` containing one page per part, displaying a line chart of its stock over time and its price over time.
