import pandas as pd
import csv

def merge_comments():
    print("Reading bom.xls...")
    df_bom = pd.read_excel('bom.xls')
    
    # Create mapping: part -> comment
    part_to_comment = {}
    for _, row in df_bom.dropna(subset=['JLCPCB Part #']).iterrows():
        p = str(row['JLCPCB Part #']).strip()
        if p.startswith('C') and p not in part_to_comment:
            part_to_comment[p] = str(row['Comment']) if pd.notna(row['Comment']) else ""
            
    print("Reading parts_results.csv...")
    results = []
    with open('parts_results.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            p = row['part']
            row['comment'] = part_to_comment.get(p, "")
            results.append(row)
            
    # Write back with comment column
    fieldnames = ['part', 'comment', 'stock', 'price']
    
    print("Writing updated parts_results.csv...")
    with open('parts_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    print("Successfully mapped comments to parts_results.csv!")

if __name__ == '__main__':
    merge_comments()
