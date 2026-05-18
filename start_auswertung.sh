#!/bin/bash
# KiBiz Verwendungsnachweis - Starter

echo "==============================================="
echo " KiBiz Kategorisierung"
echo "==============================================="

if [ "$1" == "" ]; then
    echo "Suche nach Umsaetze_*.csv im aktuellen Ordner..."
    FILE=$(ls Umsaetze_*.csv 2>/dev/null | head -n 1)
else
    FILE="$1"
fi

if [ "$FILE" == "" ]; then
    echo "FEHLER: Keine CSV-Datei gefunden!"
    echo "Bitte lege die von der Bank exportierte Datei (Umsaetze_*.csv) in diesen Ordner."
    echo "Oder starte das Skript manuell mit: ./start_auswertung.sh <pfad/zur/datei.csv>"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

echo "Verarbeite Datei: $FILE"
echo ""

# Ausführen des Python-Skripts
python3 kibiz_categorize.py "$FILE"

echo ""
echo "==============================================="
echo " FERTIG! Ergebnisse gespeichert in:"
echo " - kibiz_summen_abgabebereit.csv"
echo " - kibiz_einzelbuchungen_kontrolle.csv"
echo "==============================================="
read -p "Drücke Enter zum Beenden..."
