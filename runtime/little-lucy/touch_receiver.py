#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json, time

HOST = "192.168.31.125"
PORT = 18791
LOG = Path("/tmp/lucy-nest-touch.jsonl")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK\n"); return
        if parsed.path != "/touch":
            self.send_response(404); self.end_headers(); return
        q = parse_qs(parsed.query)
        evt = {
            "ts": time.time(),
            "x": q.get("x", [""])[0],
            "y": q.get("y", [""])[0],
            "down": q.get("down", [""])[0],
            "raw": q.get("raw", [""])[0],
        }
        with LOG.open("a", encoding="utf-8") as f: f.write(json.dumps(evt) + "\n")
        print(json.dumps(evt), flush=True)
        self.send_response(204); self.end_headers()
    def log_message(self, fmt, *args):
        return

HTTPServer((HOST, PORT), Handler).serve_forever()
