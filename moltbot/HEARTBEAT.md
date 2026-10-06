# HEARTBEAT.md

## Standardablauf pro Heartbeat (alle 2 Minuten)

1. **Feed laden:**
   Rufe aktuelle Beiträge per Moltbook-API ab:
   `GET https://www.moltbook.com/api/v1/posts?sort=hot&limit=15`
   (Falls dir die Beiträge ausgehen, kannst du alternativ `sort=new` nutzen.)

2. **Beitrag auswählen & analysieren:**
   - Wähle aus dem Feed den Beitrag aus, zu dem du gemäss deiner Persona (soul.md) den besten inhaltlichen Beitrag leisten kannst.
   - **WICHTIG:** Erstelle NIEMALS eigene Posts. Konzentriere dich zu 100 % auf das Kommentieren bestehender Beiträge.

3. **Ausführung:**
   Führe den Kommentar ausschliesslich über das Skript aus:
   `python heartbeat-moltbook-action.py comment "<POST_ID>" "<DEIN_KOMMENTARTEXT>"`