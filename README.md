# Masterprojekt: Autonome Agenten-Interaktion auf Moltbook

Dieses Forschungsprojekt untersucht das Interaktionsverhalten autonomer KI-Agenten auf der Social-Media-Plattform Moltbook. Das Experiment folgt einem **sequentiellen Design**: Ein Agent wird nacheinander in zwei verschiedenen Persönlichkeitsprofilen (Phasen) betrieben.

---

## 0. ZWINGENDE VORAUSSETZUNG: OpenClaw Framework

Dieses Projekt ist eine Erweiterung für das **OpenClaw Framework**.

1. **Installation:** Das Framework muss global installiert sein (i.d.R. via npm: `npm install -g @openclaw/gateway`).
2. **Verifizierung:** Öffne dein Terminal und tippe:
    ```bash
    openclaw --version
    ```
    *Erforderliche Version für dieses Projekt: >= 2026.4.12*

---

## 1. Verzeichnisstruktur

Das Projekt ist lokal unter `C:\Master Projekt\Moltbots\` wie folgt strukturiert:

* `\moltbot\`: Der aktive Arbeitsordner des Agenten (hier greift OpenClaw zu).
* `\souls\`: Archiv für die Persönlichkeitsprofile (`soul_good.md`, `soul_neutral.md`).
* `\templates\`: Vorlagen für Konfigurationsdateien.

---

## 2. API-Logik & Wissenschaftliches Design

Um Variablen zu kontrollieren, nutzen wir ein **Single-Agent-Setup** mit manuellem Phasenwechsel.

### A. Gemeinsames "Gehirn" (OpenAI API)
- Beide Phasen nutzen das identische Modell (GPT-Modell via OpenAI).
- Die Verhaltensänderung wird ausschließlich durch den Austausch der `soul.md` gesteuert.

### B. "Identität" (Moltbook Credentials)
- Jede Phase nutzt einen eigenen Moltbook-Account, um die Datenströme auf der Plattform sauber zu trennen. Die Zugangsdaten liegen in `\moltbot\moltbook-credentials.json`.

---

## 3. System-Integration (openclaw.json)

Registriere den Experiment-Agenten in deiner globalen OpenClaw-Konfiguration (`C:\Users\DEIN_NAME\.openclaw\openclaw.json`). Der Heartbeat-Takt ist auf 5 Minuten festgelegt:

```json
{
  "agents": {
    "list": [
      {
        "id": "moltbot",
        "name": "Moltbot-Experiment",
        "workspace": "C:\\Master Projekt\\Moltbots\\moltbot",
        "agentDir": "C:\\Master Projekt\\Moltbots\\moltbot",
        "heartbeat": {
          "every": "5m",
          "prompt": "Prüfe Moltbook gemäß deiner HEARTBEAT.md. Kommentiere einen Post oder verfasse einen eigenen. Protokolliere die Aktion UNBEDINGT als neue Zeile in aktivitaet.log im CSV-Format (Zeit;Datum;Gefundener Post;Verfasster Text;Link;Status)!"
        }
      }
    ]
  }
}

## 4. Durchführung des Phasenwechsels (Reset-Protokoll)

Beim Wechsel von Phase 1 (Good) zu Phase 2 (Neutral) muss dieses Protokoll strikt befolgt werden, um "Daten-Leckagen" und einen Context Overflow zu verhindern:

### Schritt 1: System-Stopp
Beende das Gateway im Terminal (`Strg + C` oder `taskkill /F /IM node.exe`).

### Schritt 2: Lokale Datenreinigung (Agenten-Ebene)
Lösche im Projektverzeichnis `C:\Master Projekt\Moltbots\moltbot\` folgende temporäre Dateien, falls vorhanden:
* `action.json`
* `action_result.json`
* `feed.json`
* `post_action.py`
* Alle Inhalte in den Ordnern `\memory\` und `\state\` (die Ordner selbst bleiben bestehen).

### Schritt 3: Globaler Reset (System-Ebene)
Lösche die Inhalte folgender Ordner unter `C:\Users\DEIN_NAME\.openclaw\`, um das Gedächtnis des Frameworks vollständig zurückzusetzen (Ordnerstrukturen nicht löschen):
* `\agents\moltbot\sessions\` (Löscht die `.jsonl`-Sitzungsprotokolle; zwingend erforderlich gegen Context Overflow).
* `\workspace-moltbot\` (Leert die gespiegelten Arbeitskopien).
* `\memory\` (Löscht das Vektor-Langzeitgedächtnis).
* `\completions\` (Leert den KI-Antwort-Cache).
* `\logs\` (Startet eine frische System-Protokollierung).

### Schritt 4: Profil-Update
1. Kopiere den Inhalt von `\souls\soul_neutral.md` in die aktive `\moltbot\soul.md`.
2. Aktualisiere die `\moltbot\moltbook-credentials.json` mit den Zugangsdaten des neutralen Accounts.
3. Leere den Inhalt der `\moltbot\aktivitaet.log`, damit die Messung für Phase 2 bei Zeile 1 beginnt.

### Schritt 5: Neustart
Starte das Gateway über die PowerShell neu:
```bash
openclaw gateway