# KiBiz Verwendungsnachweis Automatisierung 📊

Dieses Projekt automatisiert die Zuordnung und Auswertung von Bankumsätzen für den jährlichen **KiBiz Verwendungsnachweis** (Kinderbildungsgesetz NRW) für Kindertagesstätten und Elterninitiativen.

Die Applikation wandelt unstrukturierte CSV-Bankexporte (z.B. von der Volksbank) in saubere, KiBiz-konforme Kategorien um und bereitet die Summen so auf, dass sie direkt in das offizielle Web-Portal übertragen werden können. 

## Features ✨
- **Intelligente Kategorisierung:** Weist Bankumsätze automatisch den Kategorien "2.1.1 pädagogisches Personal", "2.4 Sachkosten", "1.1 Zuschuss" etc. zu.
- **Einfache Pflege:** Keine Programmierkenntnisse nötig! Neue Lieferanten und Kategorien können in einer einfachen Excel/CSV-Liste (`kategorien_mapping.csv`) gepflegt werden.
- **Moderne Web-App:** Ein wunderschönes, benutzerfreundliches Drag-&-Drop-Webinterface im Premium-Design.
- **Cloud Ready:** Die gesamte Architektur ist zustandslos (stateless) und vorbereitet für den Betrieb in Serverless-Umgebungen wie Google Cloud Run.
- **Datensicherheit:** Keine Speicherung von Finanzdaten auf der Festplatte des Servers – alles wird ausschließlich In-Memory verarbeitet.

## Lokale Ausführung 🚀

### Voraussetzungen
- Python 3.10+
- (Optional) Eine virtuelle Umgebung (venv)

### Installation
1. Repository klonen:
   ```bash
   git clone https://github.com/PaulAnderie/Kinderhaus_KiBiz.git
   cd Kinderhaus_KiBiz
   ```
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

### Starten der Web-App
Du kannst die Anwendung bequem über das beiliegende Start-Skript hochfahren:
```bash
./start_webapp.sh
```
Die Seite ist dann lokal unter `http://127.0.0.1:5000` erreichbar.

## Bedienung (Der Ablauf) 📝
1. Exportiere im Online-Banking deines Kinderhauses die Umsätze für das gesamte Kindergartenjahr (z.B. 01.08.2024 bis 31.07.2025) als **CSV-Datei**.
2. Ziehe diese Datei in das Upload-Feld der Web-App.
3. Die Auswertung erfolgt in Sekundenbruchteilen. Lade dir anschließend die beiden CSV-Dateien herunter:
   - `kibiz_summen_abgabebereit.csv`: Die fertigen Summen zum Abtippen.
   - `kibiz_einzelbuchungen_kontrolle.csv`: Die Nachweis-Liste, um z.B. zu prüfen, wo Ausgaben aus "Ungeklärt" hingehören.
4. Falls ein Lieferant als "Ungeklärt" auftaucht, öffne die Datei `kategorien_mapping.csv` und ergänze sein Schlagwort (z.B. `Bäckerei Müller`) und die Kategorie (`2.4 Sachkosten`). Beim nächsten Upload ist er automatisch zugeordnet!

## Deployment (Google Cloud Run) ☁️
Das Repository enthält bereits einen CI/CD Workflow für **GitHub Actions**.

1. Konfiguriere in GitHub in den Settings unter *Secrets and variables -> Actions* die folgenden Secrets:
   - `GCP_PROJECT`: Deine Google Cloud Projekt-ID.
   - `GCP_CREDENTIALS`: Deinen Service-Account-Schlüssel (JSON).
2. Sobald du Änderungen (wie z.B. eine erweiterte `kategorien_mapping.csv`) in den `main`-Branch pushst, baut GitHub den Docker-Container und veröffentlicht ihn automatisch auf Google Cloud Run.

## Verwendete Technologien 🛠
- **Backend:** Python, Flask, Pandas, Gunicorn
- **Frontend:** HTML5, Vanilla JS, Custom CSS (Glassmorphism, Dark-Mode)
- **Deployment:** Docker, GitHub Actions, Google Cloud Run
