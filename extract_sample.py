import sys
import pdfplumber
import json

def extract_pdf_data(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages):
            print(f"--- Page {i+1} Text ---")
            print(page.extract_text())
            print(f"--- Page {i+1} Tables ---")
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        print(row)
            else:
                print("No tables found by extract_tables().")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        extract_pdf_data(sys.argv[1])
    else:
        print("Please provide a PDF path.")
