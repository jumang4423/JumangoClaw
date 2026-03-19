# JLCPCB Stock and Price Tracker Skill
The `./jlcpcb` directory contains tools to scrape and track JLCPCB/LCSC part prices and stock levels.
It uses Playwright to read `bom.xls` and saves prices to a timestamped CSV.

To fetch the latest part data from JLCPCB:
```bash
cd ./jlcpcb && make refresh
# or run `python3 fetch_parts.py`
```

To compile all historical data into a PDF report graph (`./jlcpcb/parts_report.pdf`):
```bash
cd ./jlcpcb && make pdf
# or run `python3 generate_report.py`
```
After generating the PDF, you MUST use the `send_file` tool to send the path `./jlcpcb/parts_report.pdf` directly to the user.
