import pandas as pd
import re
import os
import sys
import glob
import io

def load_mapping(mapping_file):
    """Liest die Mapping-CSV und gibt ein Dictionary mit Suchbegriff -> Kategorie zurück."""
    if not os.path.exists(mapping_file):
        print(f"Warnung: Mapping-Datei '{mapping_file}' nicht gefunden. Es werden keine Regeln angewendet.")
        return {}
        
    df_map = pd.read_csv(mapping_file, sep=';', encoding='utf-8')
    mapping = {}
    for _, row in df_map.iterrows():
        suchbegriff = str(row['Suchbegriff']).strip().lower()
        kategorie = str(row['Kategorie']).strip()
        if suchbegriff and kategorie:
            mapping[suchbegriff] = kategorie
    return mapping

def categorize(row, mapping):
    # Bei Bank-CSVs nutzen wir 'Name Zahlungsbeteiligter' und 'Verwendungszweck' (oder 'Buchungstext')
    name = str(row.get('Name Zahlungsbeteiligter', '')).lower()
    vwz = str(row.get('Verwendungszweck', '')).lower()
    text = str(row.get('Buchungstext', '')).lower()
    combined = f"{name} {vwz} {text}"
    
    # Prüfe alle Suchbegriffe
    for suchbegriff, kategorie in mapping.items():
        # Exakte Wortgrenzen für kurze Begriffe, bei längeren reicht normales in
        if len(suchbegriff) <= 4:
            if re.search(r'\b' + re.escape(suchbegriff) + r'\b', combined):
                return kategorie
        else:
            if suchbegriff in combined:
                return kategorie
                
    # Restliche Einnahmen (wenn Betrag positiv ist)
    betrag = row.get('Betrag_parsed', 0.0)
    if betrag > 0:
        return '1.5 Sonstige Erträge'
        
    return 'Ungeklärt'

def parse_amount(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def find_input_csv():
    """Findet eine Bank-CSV, z.B. wenn sie als Argument übergeben wurde."""
    if len(sys.argv) > 1:
        return sys.argv[1]
        
    # Suche nach 'Umsaetze_*.csv' im aktuellen Verzeichnis
    files = glob.glob("Umsaetze_*.csv")
    if files:
        return files[0]
        
    return None

def process_csv(input_files, mapping_file='kategorien_mapping.csv'):
    # Ensure input_files is a list
    if isinstance(input_files, str):
        input_files = [input_files]
        
    # Lade Mapping
    mapping = load_mapping(mapping_file)
    
    dfs = []
    for f in input_files:
        if isinstance(f, str) and not os.path.exists(f):
            raise FileNotFoundError(f"Fehler: Bank-CSV nicht gefunden: {f}")
        # Reset position if it's a file-like object and has seek
        if hasattr(f, 'seek'):
            f.seek(0)
        df_part = pd.read_csv(f, sep=';', encoding='utf-8', encoding_errors='replace')
        dfs.append(df_part)
        
    if not dfs:
        raise ValueError("Fehler: Keine Daten zum Verarbeiten übergeben.")
        
    # Lade CSV (Bank Export ist meist mit ';' getrennt)
    df = pd.concat(dfs, ignore_index=True)
    
    if 'Buchungstag' not in df.columns:
        raise ValueError("Fehler: Die Spalte 'Buchungstag' wurde nicht gefunden. Ist es das richtige Volksbank-CSV-Format?")
        
    # Datum parsen
    df['Datum'] = pd.to_datetime(df['Buchungstag'], format="%d.%m.%Y", errors='coerce')
    
    # Betrag parsen (sind im Format -50,00 oder 123,45)
    df['Betrag_parsed'] = df['Betrag'].apply(parse_amount)
    
    # Kategorisieren
    df['Zugeordnete_Kategorie'] = df.apply(lambda row: categorize(row, mapping), axis=1)
    
    # Generate Output 1: Einzelbuchungen Kontrolle
    output_cols = ['Buchungstag', 'Name Zahlungsbeteiligter', 'Buchungstext', 'Verwendungszweck', 'Betrag', 'Zugeordnete_Kategorie']
    output_cols = [c for c in output_cols if c in df.columns]
    
    df_kontrolle = df[output_cols].copy()
    
    def adjust_sum(row):
        cat = row['Zugeordnete_Kategorie']
        val = row['Betrag_parsed']
        if cat.startswith('2.'):
            return -val
        return val
        
    df['Betrag_KiBiz'] = df.apply(adjust_sum, axis=1)
    
    # Speichern in Memory
    buf_kontrolle = io.StringIO()
    df_kontrolle.to_csv(buf_kontrolle, index=False, sep=';', encoding='utf-8-sig')
    csv_kontrolle_str = buf_kontrolle.getvalue()
    
    # Generate Output 2: Summen Abgabebereit
    summary = df.groupby('Zugeordnete_Kategorie')['Betrag_KiBiz'].sum().reset_index()
    summary = summary.rename(columns={'Zugeordnete_Kategorie': 'Kategorie', 'Betrag_KiBiz': 'Summe (EUR)'})
    
    summary['Summe (EUR)'] = summary['Summe (EUR)'].round(2)
    
    all_categories = [
        '1.1 Zuschuss', '1.5 Sonstige Erträge', 
        '2.1.1 pädagogisches Personal', '2.1.2 nicht-pädagogisches Personal', 
        '2.1.3 sonstige Personalkosten', '2.2 Investitionsaufwendungen', 
        '2.3 Miete', '2.4 Sachkosten', '2.5 Verwaltungskosten', 'Ungeklärt'
    ]
    
    for cat in all_categories:
        if cat not in summary['Kategorie'].values:
            new_row = pd.DataFrame({'Kategorie': [cat], 'Summe (EUR)': [0.00]})
            summary = pd.concat([summary, new_row], ignore_index=True)
            
    summary['SortKey'] = summary['Kategorie'].apply(lambda x: x if x != 'Ungeklärt' else '9.9')
    summary = summary.sort_values('SortKey').drop(columns=['SortKey'])
    
    summary['Summe formatiert'] = summary['Summe (EUR)'].apply(lambda x: f"{x:.2f}".replace('.', ','))
    
    summary_export = summary[['Kategorie', 'Summe formatiert']]
    buf_summen = io.StringIO()
    summary_export.to_csv(buf_summen, index=False, sep=';', encoding='utf-8-sig')
    csv_summen_str = buf_summen.getvalue()
    
    # Return dictionary for the webapp
    results = []
    for _, row in summary.iterrows():
        results.append({
            'kategorie': row['Kategorie'],
            'summe_eur': float(row['Summe (EUR)']),
            'summe_formatiert': row['Summe formatiert']
        })
        
    return {
        'total_rows': len(df),
        'summary': results,
        'csv_summen': csv_summen_str,
        'csv_kontrolle': csv_kontrolle_str
    }

def main():
    input_file = find_input_csv()
    if not input_file:
        print("Fehler: Keine Bank-CSV gefunden.")
        sys.exit(1)
        
    print(f"Verarbeite: {input_file}")
    res = process_csv(input_file)
    
    # Wenn von CLI gestartet, schreibe die Ergebnisse auf die Festplatte
    with open('kibiz_summen_abgabebereit.csv', 'w', encoding='utf-8-sig') as f:
        f.write(res['csv_summen'])
    with open('kibiz_einzelbuchungen_kontrolle.csv', 'w', encoding='utf-8-sig') as f:
        f.write(res['csv_kontrolle'])
        
    print("\n--- Zusammenfassung ---")
    for row in res['summary']:
        print(f"{row['kategorie']:35}: {row['summe_eur']:10.2f} €")
    print("\nDateien gespeichert.")

if __name__ == "__main__":
    main()
