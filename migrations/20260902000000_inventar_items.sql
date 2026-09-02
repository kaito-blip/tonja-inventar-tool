-- Inventar-Tool (frontend/inventar.html) — Bestandsführung Tonja-Boutiquen.
-- Written by backend/inventar.py via PostgREST (service key).
--
-- Additive and replay-safe (IF NOT EXISTS, seed guarded), so re-running it
-- cannot break anything. Run manually in the Supabase dashboard (SQL editor)
-- — the established workflow for this repo.

CREATE TABLE IF NOT EXISTS public.inventar_items (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at  timestamptz NOT NULL DEFAULT now(),
  name        text NOT NULL,
  marke       text NOT NULL DEFAULT '',
  kategorie   text NOT NULL
              CHECK (kategorie IN ('Damen', 'Accessoires', 'ARCHIVES', 'Sonstiges')),
  standort    text NOT NULL
              CHECK (standort IN ('Basel', 'Basel ARCHIVES', 'Gstaad', 'Genf', 'Lager')),
  bestand     integer NOT NULL DEFAULT 0 CHECK (bestand >= 0),
  min_bestand integer NOT NULL DEFAULT 1 CHECK (min_bestand >= 0),
  notiz       text NOT NULL DEFAULT '',
  -- Bis zu 3 Artikel-Fotos als data:image-URLs (client-seitig verkleinert).
  fotos       jsonb NOT NULL DEFAULT '[]'::jsonb
);

-- List view reads grouped by standort, sorted by name.
CREATE INDEX IF NOT EXISTS inventar_items_standort_name_idx
  ON public.inventar_items (standort, name);

-- Service-role access only (backend uses the service key; no anon access).
ALTER TABLE public.inventar_items ENABLE ROW LEVEL SECURITY;

-- Lieferscheine & Boxen: abfotografierte Lieferscheine mit optionalem Titel.
-- foto = data:image-URL (client-seitig auf max. 1000px verkleinert, JPEG).
CREATE TABLE IF NOT EXISTS public.inventar_lieferscheine (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  titel      text NOT NULL DEFAULT '',
  foto       text NOT NULL
);

CREATE INDEX IF NOT EXISTS inventar_lieferscheine_created_idx
  ON public.inventar_lieferscheine (created_at DESC);

-- Service-role access only (wie inventar_items).
ALTER TABLE public.inventar_lieferscheine ENABLE ROW LEVEL SECURITY;

-- Seed: Beispielartikel aus der Tonja-Welt — nur wenn die Tabelle leer ist,
-- damit ein erneutes Ausführen keine Duplikate erzeugt.
INSERT INTO public.inventar_items (name, marke, kategorie, standort, bestand, min_bestand, notiz)
SELECT * FROM (VALUES
  ('Seidentuch «Jardin» 90x90',      'Pierre-Louis Mascia', 'Accessoires', 'Basel',          4, 2, 'Bestseller — Schaufenster'),
  ('Seidentuch «Aurora» 70x70',      'Pierre-Louis Mascia', 'Accessoires', 'Genf',           1, 2, ''),
  ('Cashmere-Pullover V-Neck beige', 'Max&Moi',             'Damen',       'Basel',          3, 2, 'Grössen S–L gemischt'),
  ('Cashmere-Cardigan grau',         'Max&Moi',             'Damen',       'Gstaad',         0, 1, 'Nachbestellung angefragt'),
  ('Cashmere-Schal camel',           'Max&Moi',             'Accessoires', 'Gstaad',         5, 2, ''),
  ('Vintage-Blazer Tweed 90s',       'Chanel',              'ARCHIVES',    'Basel ARCHIVES', 1, 1, 'Einzelstück, Gr. 38'),
  ('Foulard Vintage «Cavalcadour»',  'Hermès',              'ARCHIVES',    'Basel ARCHIVES', 0, 1, 'Verkauft 28.08. — Zulauf prüfen'),
  ('Abendkleid Seide midnight',      'Tonja Collection',    'Damen',       'Genf',           2, 1, ''),
  ('Ledergürtel schmal cognac',      'Tonja Collection',    'Accessoires', 'Lager',          8, 3, 'Nachschub für alle Standorte'),
  ('Geschenkboxen-Set gross',        '',                    'Sonstiges',   'Lager',          12, 5, 'Verpackungsmaterial')
) AS seed(name, marke, kategorie, standort, bestand, min_bestand, notiz)
WHERE NOT EXISTS (SELECT 1 FROM public.inventar_items);
