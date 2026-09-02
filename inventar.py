"""Inventar-Tool (frontend/inventar.html) — provisorische Bestandsführung Tonja.

Boutique-Team pflegt Artikel (Name, Marke, Kategorie, Standort, Bestand,
Mindestbestand, Notiz) über eine schlanke Mobile-first-Oberfläche. Bestand
unter Mindestbestand wird als «Fast leer», Bestand 0 als «Ausverkauft»
markiert.

Persistenz: Supabase-Tabelle `inventar_items` via PostgREST (Service-Key).
Migration: supabase/migrations/20260902000000_inventar_items.sql — wird wie
etabliert manuell im Supabase-Dashboard ausgeführt. Fehlt die Tabelle,
antwortet das Backend mit einem klaren Hinweis statt einem 500er.

Auth = Codebesitz (wie Überstunden-/Dienstplan-Tool): ein gemeinsamer
Zugangscode, den das Frontend nach dem Login als Bearer-Token mitschickt.
"""

import hmac
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

ACCESS_CODE = os.environ.get('INVENTAR_CODE', 'tonja-inventar')

TABLE = 'inventar_items'
KATEGORIEN = ('Damen', 'Accessoires', 'ARCHIVES', 'Sonstiges')
STANDORTE = ('Basel', 'Basel ARCHIVES', 'Gstaad', 'Genf', 'Lager')
UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
MAX_BESTAND = 100000

_ssl_ctx = ssl.create_default_context()

MISSING_TABLE_MSG = 'Tabelle inventar_items fehlt — Migration ausführen'


class MissingTableError(Exception):
    pass


# ------------------------------------------------------------------
# Supabase PostgREST helper (bewusst aus server.py dupliziert — das
# Sub-Modul importiert nichts aus dem 9k-Zeilen-Server)
# ------------------------------------------------------------------

def _db(method, path, body=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception('Supabase not configured')
    url = f'{SUPABASE_URL}/rest/v1/{path}'
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=15) as resp:
            payload = resp.read()
            return json.loads(payload) if payload else []
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')
        # PGRST205 / 42P01: Tabelle (noch) nicht vorhanden -> klarer Hinweis
        if e.code == 404 or 'PGRST205' in detail or '42P01' in detail:
            raise MissingTableError(MISSING_TABLE_MSG)
        raise Exception(f'Supabase error {e.code}: {detail}')


# ------------------------------------------------------------------
# Auth + validation
# ------------------------------------------------------------------

def _authed(handler):
    auth = handler.headers.get('Authorization', '')
    token = auth[7:] if auth.startswith('Bearer ') else ''
    return bool(token) and hmac.compare_digest(token, ACCESS_CODE)


def _int(value, lo, hi):
    """Parse an int in [lo, hi] or return None."""
    try:
        i = int(value)
    except (TypeError, ValueError):
        return None
    if i < lo or i > hi:
        return None
    return i


def _validate(b, partial=False):
    """Validate item fields from a request body.

    Returns (fields, error). With partial=True only the provided keys are
    validated (PATCH); otherwise name/kategorie/standort are required.
    """
    fields = {}
    if 'name' in b or not partial:
        name = str(b.get('name', '')).strip()
        if not name or len(name) > 120:
            return None, 'Name fehlt oder zu lang (max. 120 Zeichen)'
        fields['name'] = name
    if 'marke' in b:
        marke = str(b.get('marke', '')).strip()
        if len(marke) > 80:
            return None, 'Marke zu lang (max. 80 Zeichen)'
        fields['marke'] = marke
    if 'kategorie' in b or not partial:
        kategorie = str(b.get('kategorie', '')).strip()
        if kategorie not in KATEGORIEN:
            return None, 'Ungültige Kategorie'
        fields['kategorie'] = kategorie
    if 'standort' in b or not partial:
        standort = str(b.get('standort', '')).strip()
        if standort not in STANDORTE:
            return None, 'Ungültiger Standort'
        fields['standort'] = standort
    if 'bestand' in b or not partial:
        bestand = _int(b.get('bestand', 0), 0, MAX_BESTAND)
        if bestand is None:
            return None, f'Bestand muss zwischen 0 und {MAX_BESTAND} liegen'
        fields['bestand'] = bestand
    if 'min_bestand' in b or not partial:
        min_bestand = _int(b.get('min_bestand', 1), 0, MAX_BESTAND)
        if min_bestand is None:
            return None, 'Ungültiger Mindestbestand'
        fields['min_bestand'] = min_bestand
    if 'notiz' in b:
        notiz = str(b.get('notiz', '')).strip()
        if len(notiz) > 300:
            return None, 'Notiz zu lang (max. 300 Zeichen)'
        fields['notiz'] = notiz
    return fields, None


# ------------------------------------------------------------------
# Handlers (in server.py ROUTES verdrahtet)
# ------------------------------------------------------------------

def handle_login(handler, match, body):
    """POST /api/inventar/login {code} -> {ok, token}."""
    code = str((body or {}).get('code', '')).strip()
    if not code or not hmac.compare_digest(code, ACCESS_CODE):
        return 401, {'error': 'Ungültiger Zugangscode'}
    return 200, {'ok': True, 'token': ACCESS_CODE}


def handle_list(handler, match, body):
    """GET /api/inventar/items -> {items, kategorien, standorte}."""
    if not _authed(handler):
        return 401, {'error': 'Ungültiger Zugangscode'}
    try:
        items = _db('GET', f'{TABLE}?select=*&order=standort.asc,name.asc')
    except MissingTableError as e:
        return 503, {'error': str(e)}
    return 200, {
        'items': items,
        'kategorien': list(KATEGORIEN),
        'standorte': list(STANDORTE),
    }


def handle_create(handler, match, body):
    """POST /api/inventar/items — Artikel anlegen."""
    if not _authed(handler):
        return 401, {'error': 'Ungültiger Zugangscode'}
    fields, err = _validate(body or {})
    if err:
        return 400, {'error': err}
    fields.setdefault('marke', '')
    fields.setdefault('notiz', '')
    try:
        rows = _db('POST', TABLE, body=fields)
    except MissingTableError as e:
        return 503, {'error': str(e)}
    return 200, {'ok': True, 'item': rows[0] if rows else fields}


def handle_update(handler, match, body):
    """PATCH /api/inventar/items/<id> — Felder/Bestand ändern."""
    if not _authed(handler):
        return 401, {'error': 'Ungültiger Zugangscode'}
    item_id = match.group(1).lower()
    if not UUID_RE.match(item_id):
        return 400, {'error': 'Ungültige Artikel-ID'}
    fields, err = _validate(body or {}, partial=True)
    if err:
        return 400, {'error': err}
    if not fields:
        return 400, {'error': 'Keine Änderungen übermittelt'}
    try:
        rows = _db('PATCH', f'{TABLE}?id=eq.{item_id}', body=fields)
    except MissingTableError as e:
        return 503, {'error': str(e)}
    if not rows:
        return 404, {'error': 'Artikel nicht gefunden'}
    return 200, {'ok': True, 'item': rows[0]}


def handle_delete(handler, match, body):
    """DELETE /api/inventar/items/<id> — Artikel löschen."""
    if not _authed(handler):
        return 401, {'error': 'Ungültiger Zugangscode'}
    item_id = match.group(1).lower()
    if not UUID_RE.match(item_id):
        return 400, {'error': 'Ungültige Artikel-ID'}
    try:
        rows = _db('DELETE', f'{TABLE}?id=eq.{item_id}')
    except MissingTableError as e:
        return 503, {'error': str(e)}
    if not rows:
        return 404, {'error': 'Artikel nicht gefunden'}
    return 200, {'ok': True}
