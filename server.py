"""Tonja Inventar-Tool — Standalone-Server (Render).

Serviert index.html und die /api/inventar/*-Endpoints aus inventar.py.
Env: SUPABASE_URL, SUPABASE_SERVICE_KEY, optional INVENTAR_CODE, PORT.
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import inventar

ROUTES = {
    'POST': [
        (re.compile(r'^/api/inventar/login$'), inventar.handle_login),
        (re.compile(r'^/api/inventar/items$'), inventar.handle_create),
    ],
    'GET': [
        (re.compile(r'^/api/inventar/items$'), inventar.handle_list),
    ],
    'PATCH': [
        (re.compile(r'^/api/inventar/items/([^/]+)$'), inventar.handle_update),
    ],
    'DELETE': [
        (re.compile(r'^/api/inventar/items/([^/]+)$'), inventar.handle_delete),
    ],
}

_HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):

    def _json(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def _api(self, method):
        body = None
        length = int(self.headers.get('Content-Length') or 0)
        if length:
            try:
                body = json.loads(self.rfile.read(length) or b'{}')
            except ValueError:
                return self._json(400, {'error': 'Ungültiges JSON'})
        for pattern, fn in ROUTES.get(method, []):
            m = pattern.match(self.path.split('?', 1)[0])
            if m:
                status, payload = fn(self, m, body)
                return self._json(status, payload)
        self._json(404, {'error': 'Nicht gefunden'})

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path.startswith('/api/'):
            return self._api('GET')
        if path in ('/', '/index.html', '/inventar.html'):
            with open(os.path.join(_HERE, 'index.html'), 'rb') as f:
                raw = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        self._json(404, {'error': 'Nicht gefunden'})

    def do_POST(self):
        self._api('POST')

    def do_PATCH(self):
        self._api('PATCH')

    def do_DELETE(self):
        self._api('DELETE')

    def log_message(self, fmt, *args):
        print('%s %s' % (self.command or '-', self.path or '-'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8080'))
    print(f'Tonja Inventar-Tool auf Port {port}')
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
