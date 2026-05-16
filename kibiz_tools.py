import csv
import re
import json

# Globale Variable für den In-Memory-Zustand des aktuellen Laufs
all_records = []

def parse_amount(amount_str: str) -> float:
    if not amount_str:
        return 0.0
    amount_str = amount_str.replace('.', '').replace(',', '.')
    try:
        return float(amount_str)
    except ValueError:
        return 0.0

def apply_fixed_rules(row_text: str, gegenkonto: str) -> str:
    text = row_text.lower()
    if re.search(r'stadt kleve|lvr|landschaftsverband', text):
        return '1.1 Zuschuss'
    if re.search(r'sonstige erträge', text):
        return '1.5 Sonstige Erträge'
    if re.search(r'aok|barmer|kkh|knappschaft|vblu|landeshauptkasse|debeka|swiss life|gehalt|lohn|tk|techniker|dak', text) or gegenkonto in ['6020', '6040']:
        return '2.1.1 pädagogisches Personal'
    if re.search(r'andreas goris|karl heinz gaßmann', text):
        return '2.3 Miete'
    if re.search(r'stadtwerke|telekom|putzstube|waterlogic|swertz|unterbichler', text):
        return '2.4 Sachkosten'
    if re.search(r'paridienst|amtsgericht|notar|gez', text):
        return '2.5 Verwaltungskosten'
    return 'Ungeklärt'

def process_bank_export(filepath: str) -> str:
    """
    Lädt den Bankexport und führt die erste automatische Kategorisierung via Regex durch.
    Gibt eine Zusammenfassung über erkannte und noch ungeklärte Posten als JSON-String zurück.
    """
    global all_records
    all_records = []
    unresolved_count = 0
    
    with open(filepath, 'r', encoding='latin1') as f:
        lines = f.readlines()
        if len(lines) > 0 and ('Kanzlei' in lines[0] or 'DATEV' in lines[0]):
            lines = lines[1:]
            
        reader = csv.DictReader(lines, delimiter=';')
        
        for i, row in enumerate(reader):
            datum = row.get('Datum', '')
            buchungstext = row.get('Buchungstext', '')
            gegenkonto = row.get('Gegenkonto', '')
            beleg = row.get('Belegfeld1', '')
            
            text_to_search = f"{buchungstext} {beleg}".strip()
            if buchungstext == 'EB-Wert':
                continue
                
            soll_str = row.get('Umsatz Soll', '')
            haben_str = row.get('Umsatz Haben', '')
            
            soll = parse_amount(soll_str)
            haben = parse_amount(haben_str)
            
            if soll == 0 and haben == 0:
                continue
                
            cat = apply_fixed_rules(text_to_search, gegenkonto)
            
            if cat.startswith('1.'):
                betrag = soll - haben
            else:
                betrag = haben - soll
                
            record = {
                'id': i,
                'Datum': datum,
                'Gegenkonto': gegenkonto,
                'Text': text_to_search,
                'Betrag': betrag,
                'Kategorie': cat
            }
            all_records.append(record)
            if cat == 'Ungeklärt':
                unresolved_count += 1
                
    return json.dumps({
        "status": "success",
        "total_records_processed": len(all_records),
        "unresolved_items_count": unresolved_count,
        "message": "Bitte nutze die Funktion get_unresolved_items_batch um die offenen Posten abzurufen."
    })

def get_unresolved_items_batch(batch_size: int = 10) -> str:
    """
    Gibt die nächste Charge von ungeklärten Posten als JSON zurück, damit das LLM sie analysieren kann.
    Jeder Posten enthält eine 'id', den 'Text' und den 'Betrag'.
    """
    global all_records
    batch = []
    for r in all_records:
        if r['Kategorie'] == 'Ungeklärt':
            batch.append({
                "id": r['id'],
                "Text": r['Text'],
                "Betrag": r['Betrag'],
                "Gegenkonto": r['Gegenkonto']
            })
            if len(batch) >= batch_size:
                break
    
    if not batch:
        return json.dumps({"status": "complete", "message": "Keine ungeklärten Posten mehr vorhanden."})
        
    return json.dumps({"status": "success", "items": batch})

def update_kibiz_categories(updates: list) -> str:
    """
    Aktualisiert die Kategorien von ungeklärten Posten.
    Erwartet eine Liste von Dictionaries mit 'id' (int) und 'category' (str).
    Zulässige Kategorien:
    '1.1 Zuschuss', '1.5 Sonstige Erträge', '2.1.1 pädagogisches Personal', '2.1.2 nicht-pädagogisches Personal', 
    '2.1.3 sonstige Personalkosten', '2.2 Investitionsaufwendungen', '2.3 Miete', '2.4 Sachkosten', '2.5 Verwaltungskosten'
    """
    global all_records
    success_count = 0
    valid_categories = [
        '1.1 Zuschuss', '1.5 Sonstige Erträge', '2.1.1 pädagogisches Personal', 
        '2.1.2 nicht-pädagogisches Personal', '2.1.3 sonstige Personalkosten', 
        '2.2 Investitionsaufwendungen', '2.3 Miete', '2.4 Sachkosten', '2.5 Verwaltungskosten',
        'Ungeklärt' # Falls es wirklich nicht zuzuordnen ist
    ]
    
    updates_dict = {u['id']: u['category'] for u in updates}
    
    for r in all_records:
        if r['id'] in updates_dict:
            new_cat = updates_dict[r['id']]
            if new_cat in valid_categories:
                r['Kategorie'] = new_cat
                success_count += 1
                
    return json.dumps({"status": "success", "updated_count": success_count})

def save_final_kibiz_export(output_prefix: str = "kibiz_agent") -> str:
    """Speichert die finalen Ergebnisse (aggregiert und einzeln) in zwei CSV-Dateien."""
    global all_records
    sums = {}
    for r in all_records:
        cat = r['Kategorie']
        sums[cat] = sums.get(cat, 0.0) + r['Betrag']
        
    sum_file = f"{output_prefix}_summen.csv"
    with open(sum_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Kategorie-Nr', 'Kategorie-Name', 'Summe (EUR)'])
        for cat, total in sorted(sums.items()):
            if ' ' in cat:
                nr, name = cat.split(' ', 1)
            else:
                nr, name = '', cat
            writer.writerow([nr, name, f"{total:.2f}".replace('.', ',')])
            
    detail_file = f"{output_prefix}_details.csv"
    with open(detail_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['ID', 'Datum', 'Gegenkonto', 'Buchungstext/Beleg', 'Betrag (EUR)', 'Kategorie'])
        for r in all_records:
            writer.writerow([
                r['id'], r['Datum'], r['Gegenkonto'], r['Text'], 
                f"{r['Betrag']:.2f}".replace('.', ','), r['Kategorie']
            ])
            
    return json.dumps({"status": "success", "message": f"Gespeichert: {sum_file} und {detail_file}"})
