import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import re
from datetime import datetime

def parse_price(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).replace('$', '').strip()
    try:
        return float(val_str)
    except:
        return 0.0

def generate_pdf():
    files = glob.glob('parts_results_*.csv')
    if not files:
        print("No parts_results files found.")
        return
        
    all_data = []
    
    for f in files:
        # Extract timestamp: parts_results_20260319_141302.csv
        match = re.search(r'parts_results_(\\d{8}_\\d{6})\\.csv', f)
        if match:
            ts_str = match.group(1)
            try:
                dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            except:
                dt = datetime.fromtimestamp(os.path.getctime(f)) # Fallback
        else:
            # Fallback for old file if any
            dt = datetime.fromtimestamp(os.path.getctime(f))
            
        df = pd.read_csv(f)
        df['date'] = dt
        all_data.append(df)
        
    if not all_data:
        print("No valid data loaded.")
        return
        
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df['price_val'] = combined_df['price'].apply(parse_price)
    
    # Sort by date for proper plotting
    combined_df.sort_values('date', inplace=True)
    
    pdf_filename = "parts_report.pdf"
    print(f"Generating {pdf_filename}...")
    
    unique_parts = combined_df['part'].dropna().unique()
    
    with PdfPages(pdf_filename) as pdf:
        for p in unique_parts:
            part_data = combined_df[combined_df['part'] == p]
            if len(part_data) == 0:
                continue
                
            comment = part_data['comment'].iloc[0] if 'comment' in part_data.columns else ""
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10))
            fig.suptitle(f'Part: {p} - {comment}', fontsize=16)
            
            # Subplot 1: Price
            ax1.plot(part_data['date'], part_data['price_val'], marker='o', color='b', linestyle='-')
            ax1.set_title('Price History (USD)')
            ax1.set_ylabel('Price ($)')
            ax1.grid(True)
            
            # Format X-axis for better date rendering
            fig.autofmt_xdate(rotation=45)
            
            # Subplot 2: Stock
            ax2.plot(part_data['date'], part_data['stock'], marker='s', color='g', linestyle='-')
            ax2.set_title('Stock History')
            ax2.set_ylabel('Units in Stock')
            ax2.grid(True)
            
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])
            pdf.savefig(fig)
            plt.close(fig)
            
    print(f"Successfully generated {pdf_filename} with {len(unique_parts)} pages.")

if __name__ == '__main__':
    generate_pdf()
