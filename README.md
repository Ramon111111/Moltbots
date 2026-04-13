# Masterprojekt: Autonome Agenten-Interaktion auf Moltbook

Dieses Forschungsprojekt untersucht das Interaktionsverhalten autonomer KI-Agenten auf der Social-Media-Plattform Moltbook. Es werden zwei Agenten-Profile verglichen: **Moltbot-Good** (pro-sozial) und **Moltbot-Neutral** (wertfrei).

---

## 0. ZWINGENDE VORAUSSETZUNG: OpenClaw Framework

Dieses Projekt ist kein eigenständiges Programm, sondern eine Erweiterung für das **OpenClaw Framework**. Bevor du startest, muss OpenClaw auf deinem Betriebssystem installiert sein.

1.  **Installation:** Das Framework muss global installiert sein (i.d.R. via npm: `npm install -g @openclaw/gateway`).
2.  **Verifizierung:** Öffne dein Terminal (PowerShell/CMD) und tippe:
    ```bash
    openclaw --version
    ```
    Erhältst du eine Fehlermeldung ("Befehl nicht gefunden"), ist das Framework nicht installiert. Ohne die globale Installation können die Agenten in diesem Repository nicht gestartet werden.

---

## 1. API-Logik (Wissenschaftliches Design)

Um die methodische Sauberkeit des Experiments zu gewährleisten, nutzen wir folgendes Setup:

### A. Gemeinsames "Gehirn" (OpenAI API)
- **Status:** Identischer Key für beide Bots.
- **Grund:** Beide Bots nutzen dieselbe Rechenpower (GPT-Modell). Da sie unterschiedliche Anweisungen (`soul.md`) haben, beeinflusst der gemeinsame Key nicht ihr unterschiedliches Verhalten.

### B. Getrennte "Identität" (Moltbook Credentials)
- **Status:** Zwingend unterschiedliche Keys/Accounts.
- **Grund:** Jeder Bot muss als eigenständiges Individuum auf der Plattform auftreten. Würden sie denselben Key nutzen, würden sie unter demselben Namen posten, was einen Vergleich unmöglich machen würde.

---

## 2. Lokale Einrichtung

### Schritt 1: Repository klonen
Klone diesen Ordner in dein lokales Verzeichnis: `C:\Moltbots\`.

### Schritt 2: Keys einfügen (Templates nutzen)
Kopiere die Vorlagen aus dem Ordner `/templates` in die jeweiligen Bot-Ordner (`/moltbot-good` und `/moltbot-neutral`):

1.  **auth-profiles.json**: Erstelle diese Datei aus der Vorlage und füge deinen **OpenAI-Key** ein.
2.  **moltbook-credentials.json**: Erstelle diese Datei aus der Vorlage und füge die **spezifischen Moltbook-Daten** (Key, ID, Name) des jeweiligen Accounts ein.

---

## 3. System-Integration (openclaw.json)

Damit das installierte OpenClaw-Framework weiß, wo deine Masterarbeit-Agenten liegen, musst du sie in der **globalen Konfiguration** anmelden:

1.  Öffne die Datei: `C:\Users\DEIN_NAME\.openclaw\openclaw.json`
2.  Füge die Pfade zu den beiden Ordnern in die `list` ein:

```json
"list": [
  {
    "id": "moltbot-good",
    "name": "Moltbot-Good",
    "workspace": "C:\\\\Moltbots\\\\moltbot-good",
    "agentDir": "C:\\\\Moltboots\\\\moltbot-good"
  },
  {
    "id": "moltbot-neutral",
    "name": "Moltbot-Neutral",
    "workspace": "C:\\\\Moltbots\\\\moltbot-neutral",
    "agentDir": "C:\\\\Moltbots\\\\moltbot-neutral"
  }
]