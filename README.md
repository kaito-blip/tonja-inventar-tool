# Tonja Inventar-Tool

Provisorische Bestandsführung für Tonja Concept (Boutiquen Basel, Gstaad, Genf, Lager).
Apple-Style-Frontend, Python-Backend, Supabase-Persistenz. Login per Zugangscode.

## Setup
1. **Supabase:** `migrations/20260902000000_inventar_items.sql` im SQL-Editor ausführen (legt Tabelle + Seed an).
2. **Render:** New → Blueprint → dieses Repo wählen (render.yaml wird erkannt). Env-Vars setzen:
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, optional `INVENTAR_CODE` (Fallback: tonja-inventar).
3. Aufrufen: `https://<service>.onrender.com/` → Zugangscode eingeben.

## Pflege
- Artikelfelder: Name, Marke, Kategorie, Standort, Bestand, Mindestbestand, Notiz.
- Bestand < Mindestbestand → «Fast leer», 0 → «Ausverkauft».
