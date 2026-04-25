# Masterprojekt: Autonome Agenten-Interaktion auf Moltbook

Dieses Forschungsprojekt untersucht das Interaktionsverhalten autonomer KI-Agenten auf der Social-Media-Plattform Moltbook. Das Experiment folgt einem **sequentiellen Design**: Ein Agent wird nacheinander in zwei verschiedenen Persönlichkeitsprofilen (Phasen) betrieben.

---

## 0. ZWINGENDE VORAUSSETZUNG: OpenClaw Framework

Dieses Projekt ist eine Erweiterung für das **OpenClaw Framework**.

1.  **Installation:** Das Framework muss global installiert sein (i.d.R. via npm: `npm install -g @openclaw/gateway`).
2.  **Verifizierung:** Öffne dein Terminal und tippe:
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

Registriere den Experiment-Agenten in deiner globalen OpenClaw-Konfiguration (`C:\Users\DEIN_NAME\.openclaw\openclaw.json`):

```json
{
  "agents": {
    "list": [
      {
        "id": "moltbot",
        "name": "Moltbot-Experiment",
        "workspace": "C:\\Master Projekt\\Moltbots\\moltbot",
        "agentDir": "C:\\Master Projekt\\Moltbots\\moltbot"
      }
    ]
  }
}


## 4. Durchführung des Phasenwechsels (Reset-Protokoll)
Beim Wechsel von Phase 1 (Good) zu Phase 2 (Neutral) muss dieses Protokoll strikt befolgt werden, um "Daten-Leckagen" zu verhindern:

Schritt 1: System-Stopp
Beende das Gateway im Terminal (Strg + C oder taskkill /F /IM node.exe).

Schritt 2: Lokale Datenreinigung (Agenten-Ebene)
Lösche alle Dateien im Ordner \Moltbots\moltbot\sessions\.

Lösche alle tmp_-Dateien im Ordner \Moltbots\moltbot\.

Schritt 3: Globaler Reset (System-Ebene)
Lösche (oder sichere extern) die Inhalte folgender Ordner unter C:\Users\DEIN_NAME\.openclaw\:

\memory\ (Löscht das Vektor-Langzeitgedächtnis).

\logs\ (Startet eine frische Protokollierung für Phase 2).

\completions\ (Leert den KI-Antwort-Cache).

Schritt 4: Profil-Update
Kopiere den Inhalt von \souls\soul_neutral.md in die aktive \moltbot\soul.md.

Aktualisiere die \moltbot\moltbook-credentials.json mit den Daten des neutralen Accounts.

Schritt 5: Neustart
Starte das Gateway neu: openclaw gateway.
