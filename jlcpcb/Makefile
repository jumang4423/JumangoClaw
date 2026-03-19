.PHONY: refresh pdf help

help:
	@echo "Available commands:"
	@echo "  make refresh - Scrapes current data from JLCPCB and creates a new parts_results CSV"
	@echo "  make pdf     - Merges all timestamped parts_results CSVs and generates the PDF report"

refresh:
	python3 fetch_parts.py

pdf:
	python3 generate_report.py
