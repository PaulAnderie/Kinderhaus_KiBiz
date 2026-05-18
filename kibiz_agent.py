import os
import json
from google.adk.agents.llm_agent import Agent

import kibiz_tools

# Definiere Wrapper-Funktionen als ADK Tools
def process_export_tool(filepath: str) -> str:
    """Verarbeitet die initiale Bank Export Datei und wendet fixe Regeln an."""
    return kibiz_tools.process_bank_export(filepath)

def get_unresolved_batch_tool() -> str:
    """Holt die nächste Charge von ungeklärten Posten zur Analyse."""
    return kibiz_tools.get_unresolved_items_batch(batch_size=20)

def update_categories_tool(updates_json: str) -> str:
    """
    Aktualisiert die Kategorien der ungeklärten Posten.
    Erwartet einen JSON-String mit einer Liste von Updates.
    Beispiel: '[{"id": 1, "category": "2.4 Sachkosten"}]'
    """
    try:
        updates = json.loads(updates_json)
        return kibiz_tools.update_kibiz_categories(updates)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def save_results_tool() -> str:
    """Speichert die finalen Ergebnisse in CSV Dateien."""
    return kibiz_tools.save_final_kibiz_export()

# Agent Initialisierung
kibiz_agent = Agent(
    model='gemini-1.5-pro',
    name='KiBiz_Categorizer',
    description='Ein Agent, der Finanzdaten für den jährlichen KiBiz-Verwendungsnachweis aufbereitet und kategorisiert.',
    instruction='''Du bist ein intelligenter Finanzassistent für ein Kinderhaus.
Deine Aufgabe ist es, einen Bank-Export einzulesen, vorläufig kategorisierte Daten zu sichten und für ungeklärte Posten die passende KiBiz-Kategorie zu finden.

Der Ablauf:
1. Rufe das Tool `process_export_tool` mit der gewünschten CSV-Datei auf.
2. Wenn ungeklärte Posten vorhanden sind, rufe wiederholt `get_unresolved_batch_tool` auf.
3. Analysiere jeden ungeklärten Posten anhand des Buchungstextes (Text) und Gegenkontos. Ermittle ob es sich z.B. um Sachkosten (Baufirmen, Amazon, Handwerker, Spielzeug), Verwaltungskosten (Bankgebühren, Notar, Steuerberater) oder Sonstige Personalkosten handelt.
4. Rufe `update_categories_tool` mit deinen Zuordnungen auf (als JSON String). Nutze exakt diese Kategorienamen: '1.1 Zuschuss', '1.5 Sonstige Erträge', '2.1.1 pädagogisches Personal', '2.1.2 nicht-pädagogisches Personal', '2.1.3 sonstige Personalkosten', '2.2 Investitionsaufwendungen', '2.3 Miete', '2.4 Sachkosten', '2.5 Verwaltungskosten'.
5. Rufe am Ende `save_results_tool` auf, um die Arbeit zu beenden.
''',
    tools=[
        process_export_tool, 
        get_unresolved_batch_tool, 
        update_categories_tool, 
        save_results_tool
    ]
)

if __name__ == "__main__":
    print("KiBiz Agent ist initialisiert. Starte die Verarbeitung...")
    
    # Sicherstellen, dass der User seinen API-Key im Environment hat (notwendig für das LLM)
    if "GEMINI_API_KEY" not in os.environ:
        print("\nHINWEIS: Bitte setze die Umgebungsvariable GEMINI_API_KEY, bevor du das Skript ausführst!")
        print("Beispiel: export GEMINI_API_KEY='dein-key'\n")
    
    try:
        # Hier wird der Agent autonom auf die Reise geschickt
        response = kibiz_agent.invoke(
            "Bitte verarbeite die Datei 'Bank WJ 22-23.csv', kategorisiere alle ungeklärten Posten sorgfältig und speichere das finale Ergebnis."
        )
        print("\nAgent Ausführung beendet. Ergebnis:")
        print(response)
    except Exception as e:
        print(f"\nFehler beim Ausführen des Agenten: {e}")
