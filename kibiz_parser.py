import csv
import re

def parse_amount(amount_str):
    if not amount_str:
        return 0.0
    # Entferne Tausendertrennzeichen und ersetze Komma durch Punkt
    amount_str = amount_str.replace('.', '').replace(',', '.')
    try:
        return float(amount_str)
    except ValueError:
        return 0.0

def categorize(row_text, gegenkonto):
    text = row_text.lower()
    
    # 1.1 Zuschuss
    if re.search(r'stadt kleve|lvr|landschaftsverband', text):
        return '1.1 Zuschuss'
        
    # 1.5 Sonstige Erträge
    if re.search(r'sonstige erträge', text):
        return '1.5 Sonstige Erträge'
        
    # 2.1.1 pädagogisches Personal
    # 6020/6040 sind klassische DATEV-Konten für Gehälter/Löhne
    if re.search(r'aok|barmer|kkh|knappschaft|vblu|landeshauptkasse|debeka|swiss life|gehalt|lohn|tk|techniker|dak', text) or gegenkonto in ['6020', '6040']:
        return '2.1.1 pädagogisches Personal'
        
    # 2.3 Miete
    if re.search(r'andreas goris|karl heinz gaßmann', text):
        return '2.3 Miete'
        
    # 2.4 Sachkosten
    if re.search(r'stadtwerke|telekom|putzstube|waterlogic|swertz|unterbichler', text):
        return '2.4 Sachkosten'
        
    # 2.5 Verwaltungskosten
    if re.search(r'paridienst|amtsgericht|notar|gez', text):
        return '2.5 Verwaltungskosten'
        
    return 'Ungeklärt'

def process_file(input_file):
    records = []
    
    # DATEV-Exporte sind oft in latin1 kodiert
    with open(input_file, 'r', encoding='latin1') as f:
        lines = f.readlines()
        
        # Überspringe die erste DATEV-Kopfzeile, falls vorhanden
        if len(lines) > 0 and ('Kanzlei' in lines[0] or 'DATEV' in lines[0]):
            lines = lines[1:]
            
        reader = csv.DictReader(lines, delimiter=';')
        
        for row in reader:
            datum = row.get('Datum', '')
            buchungstext = row.get('Buchungstext', '')
            gegenkonto = row.get('Gegenkonto', '')
            beleg = row.get('Belegfeld1', '')
            
            # Kombiniere Textfelder für eine bessere Suche
            text_to_search = f"{buchungstext} {beleg}".strip()
            
            # Eröffnungsbilanzwert ignorieren
            if buchungstext == 'EB-Wert':
                continue
                
            soll_str = row.get('Umsatz Soll', '')
            haben_str = row.get('Umsatz Haben', '')
            
            soll = parse_amount(soll_str)
            haben = parse_amount(haben_str)
            
            if soll == 0 and haben == 0:
                continue
                
            cat = categorize(text_to_search, gegenkonto)
            
            # Einnahmen (1.x) sind positiv im Soll, Ausgaben negativ im Haben.
            # Für die Web-Portal-Darstellung drehen wir das Vorzeichen bei Ausgaben,
            # sodass Kosten als positive Werte in der Summe erscheinen.
            if cat.startswith('1.'):
                betrag = soll - haben
            else:
                betrag = haben - soll
                
            records.append({
                'Datum': datum,
                'Gegenkonto': gegenkonto,
                'Text': text_to_search,
                'Soll': soll,
                'Haben': haben,
                'Betrag': betrag,
                'Kategorie': cat
            })
            
    return records

def write_outputs(records):
    sums = {}
    for r in records:
        cat = r['Kategorie']
        sums[cat] = sums.get(cat, 0.0) + r['Betrag']
        
    # Summen-Datei für das Webportal
    with open('kibiz_summen_abgabebereit.csv', 'w', newline='', encoding='utf-8') as f:
        # Semikolon für einfaches Öffnen in deutschem Excel
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Kategorie-Nr', 'Kategorie-Name', 'Summe (EUR)'])
        for cat, total in sorted(sums.items()):
            if ' ' in cat:
                nr, name = cat.split(' ', 1)
            else:
                nr, name = '', cat
            writer.writerow([nr, name, f"{total:.2f}".replace('.', ',')])
            
    # Einzelbuchungen zur Kontrolle
    with open('kibiz_einzelbuchungen_kontrolle.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Datum', 'Gegenkonto', 'Buchungstext/Beleg', 'Umsatz Soll', 'Umsatz Haben', 'Verrechneter Betrag (Portal)', 'Zugeordnete_Kategorie'])
        for r in records:
            writer.writerow([
                r['Datum'], 
                r['Gegenkonto'], 
                r['Text'], 
                f"{r['Soll']:.2f}".replace('.', ','),
                f"{r['Haben']:.2f}".replace('.', ','),
                f"{r['Betrag']:.2f}".replace('.', ','), 
                r['Kategorie']
            ])

if __name__ == '__main__':
    input_filename = 'Bank WJ 22-23.csv'
    print(f"Lese Datei: {input_filename}")
    records = process_file(input_filename)
    write_outputs(records)
    print("Fertig! Es wurden folgende Dateien erstellt:")
    print("- kibiz_summen_abgabebereit.csv")
    print("- kibiz_einzelbuchungen_kontrolle.csv")
