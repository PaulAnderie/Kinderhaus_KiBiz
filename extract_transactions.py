import os
import re
import csv
import glob
import pdfplumber

def parse_transactions(pdf_path, year):
    transactions = []
    
    # Regex for start of transaction: e.g., "03.01. 31.12. Basislastschrift Ev 45,00 H"
    # Matches: Bu-Tag, Wert, Vorgang, Betrag, S/H
    tx_start_pattern = re.compile(r'^(\d{2}\.\d{2}\.)\s+(\d{2}\.\d{2}\.?\d{0,4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([HS])$')
    
    # Ignored lines that aren't part of a transaction body
    ignore_starts = [
        "Volksbank Kleverland",
        "Kontokorrent",
        "EUR-Konto",
        "Kontoauszug",
        "erstellt am",
        "IBAN:",
        "Ihr Berater:",
        "Tel:",
        "Vereinskonto",
        "Bu-Tag Wert Vorgang",
        "alter Kontostand",
        "neuer Kontostand",
        "Übertrag",
        "Bitte beachten Sie die Hinweise"
    ]
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            
            current_tx = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Skip header/footer lines if we are not currently capturing a transaction body
                is_ignored = False
                for ig in ignore_starts:
                    if line.startswith(ig) or ig in line and "Übertrag" in line:
                        is_ignored = True
                        break
                
                # Check if this line is the start of a new transaction
                match = tx_start_pattern.match(line)
                
                if match:
                    if current_tx:
                        transactions.append(current_tx)
                    
                    current_tx = {
                        "Jahr": year,
                        "Datei": os.path.basename(pdf_path),
                        "Bu-Tag": match.group(1),
                        "Wert": match.group(2),
                        "Vorgang": match.group(3).strip(),
                        "Betrag": match.group(4),
                        "Umsatzart": match.group(5),
                        "Name": "",
                        "Verwendungszweck_Lines": [],
                        "IBAN": "",
                        "BIC": ""
                    }
                    continue
                
                if current_tx and not is_ignored:
                    # Append to current transaction details
                    if not current_tx["Name"]:
                        current_tx["Name"] = line
                    else:
                        current_tx["Verwendungszweck_Lines"].append(line)
                
            if current_tx:
                transactions.append(current_tx)
                
    # Post-process transactions to extract IBAN/BIC and join Verwendungszweck
    for tx in transactions:
        vwz_joined = " ".join(tx["Verwendungszweck_Lines"])
        
        # Extract IBAN
        iban_match = re.search(r'IBAN:\s*([A-Z\s]+[\d\sA-Z]+)', vwz_joined)
        if iban_match:
            iban_raw = iban_match.group(1).split('BIC:')[0].split('0762')[0]
            tx["IBAN"] = iban_raw.replace(" ", "")
            
        # Extract BIC
        bic_match = re.search(r'BIC:\s*([A-Z0-9]+)', vwz_joined)
        if bic_match:
            tx["BIC"] = bic_match.group(1)
            
        # Clean up VWZ a bit (remove the footer text)
        vwz_clean = vwz_joined.split('0762 001')[0].strip()
        tx["Verwendungszweck"] = vwz_clean
        
    return transactions

if __name__ == "__main__":
    all_transactions = []
    
    # Process 2022 and 2023
    for year in ["2022", "2023"]:
        pdf_files = glob.glob(os.path.join(year, "*.pdf"))
        print(f"Found {len(pdf_files)} files in {year}")
        for pdf_path in pdf_files:
            try:
                txs = parse_transactions(pdf_path, year)
                all_transactions.extend(txs)
            except Exception as e:
                print(f"Error parsing {pdf_path}: {e}")
                
    print(f"Total transactions extracted: {len(all_transactions)}")
    
    # Write to CSV
    csv_file = "transactions_export.csv"
    fieldnames = ["Jahr", "Datei", "Bu-Tag", "Wert", "Vorgang", "Betrag", "Umsatzart", "Name", "Verwendungszweck", "IBAN", "BIC"]
    
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tx in all_transactions:
            # Drop the intermediate 'Verwendungszweck_Lines' key for CSV
            tx_out = {k: v for k, v in tx.items() if k in fieldnames}
            writer.writerow(tx_out)
            
    print(f"Data successfully exported to {csv_file}")
