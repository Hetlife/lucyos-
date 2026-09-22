#!/usr/bin/env python3
"""Public mobile TaskCheck surface; token-scoped, no LucyOS control credentials in browser."""
from __future__ import annotations

import argparse, json, mimetypes, os, shutil, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from aion_core import bootstrap, taskcheck  # noqa: E402

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'taskcheck_web'
MAX_JSON=64*1024
MAX_EVIDENCE=8*1024*1024


def notify_requester(taskcheck_id: str) -> dict:
    """Optional deterministic OpenClaw notification adapter. Submission remains durable if transport fails."""
    target=os.environ.get("TASKCHECK_NOTIFY_TARGET","").strip()
    binary=os.environ.get("TASKCHECK_OPENCLAW_BIN","").strip() or shutil.which("openclaw")
    if not target or not binary:
        return {"status":"NOT_CONFIGURED"}
    message=taskcheck.text_report(taskcheck_id)
    try:
        result=subprocess.run([binary,"message","send","--channel","whatsapp","--target",target,"--message",message,"--json"],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired):
        taskcheck._emit("task.notification.failed",taskcheck_id,channel="whatsapp")
        return {"status":"FAILED"}
    if result.returncode != 0:
        taskcheck._emit("task.notification.failed",taskcheck_id,channel="whatsapp")
        return {"status":"FAILED"}
    taskcheck._emit("task.notification.sent",taskcheck_id,channel="whatsapp")
    return {"status":"SENT"}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt,*args): pass
    def security(self):
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer'); self.send_header('Permissions-Policy','camera=(self), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
    def json(self,code,payload):
        body=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.security(); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def error_json(self,code,msg): self.json(code,{'ok':False,'error':msg})
    def asset(self,name):
        path=(WEB/name).resolve()
        try: path.relative_to(WEB.resolve())
        except ValueError: return self.error_json(404,'not found')
        if not path.is_file(): return self.error_json(404,'not found')
        body=path.read_bytes(); kind=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'; self.send_response(200); self.send_header('Content-Type',kind+('; charset=utf-8' if kind.startswith('text/') or kind=='application/javascript' else '')); self.security(); self.send_header('Cache-Control','public, max-age=3600'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def page(self,token):
        try: t=taskcheck.public_task(token, mark_opened=False)
        except ValueError: return self.error_json(404,'task unavailable')
        tpl=(WEB/'index.html').read_text(); title=f"LUCY TaskCheck — {t['title']}"; desc=f"{len(t['checks'])}-point inspection checklist • mobile friendly"
        proto=self.headers.get('X-Forwarded-Proto','https'); host=self.headers.get('Host',''); image=f'{proto}://{host}/taskcheck-assets/preview.png' if host else '/taskcheck-assets/preview.png'; body=tpl.replace('{{OG_TITLE}}',title).replace('{{OG_DESCRIPTION}}',desc).replace('{{OG_IMAGE}}',image).encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.security(); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def token_parts(self,path):
        parts=[x for x in path.split('/') if x]
        return parts
    def do_GET(self):
        path=urlsplit(self.path).path; parts=self.token_parts(path)
        if path=='/taskcheck-assets/app.js': return self.asset('app.js')
        if path=='/taskcheck-assets/styles.css': return self.asset('styles.css')
        if path=='/taskcheck-assets/preview.png': return self.asset('preview.png')
        if len(parts)==2 and parts[0]=='t': return self.page(parts[1])
        if len(parts)==4 and parts[:2]==['api','taskcheck'] and parts[3]=='report':
            try:
                row=taskcheck._run_for_token(parts[2]); return self.json(200,{'ok':True,'report':taskcheck.report(row['taskcheck_id'])})
            except ValueError as e: return self.error_json(404,str(e))
        if len(parts)==3 and parts[:2]==['api','taskcheck']:
            try: return self.json(200,{'ok':True,'task':taskcheck.public_task(parts[2], mark_opened=False)})
            except ValueError as e: return self.error_json(404,str(e))
        if len(parts)==3 and parts[0]=='report' and parts[2]=='LUCY-TaskCheck-report.txt':
            token=parts[1]
            try:
                row=taskcheck._run_for_token(token); text=taskcheck.text_report(row['taskcheck_id']).encode('utf-8'); self.send_response(200); self.send_header('Content-Type','text/plain; charset=utf-8'); self.send_header('Content-Disposition','attachment; filename="LUCY-TaskCheck-report.txt"'); self.send_header('Cache-Control','private, no-store'); self.security(); self.send_header('Content-Length',str(len(text))); self.end_headers(); self.wfile.write(text); return
            except ValueError: return self.error_json(404,'report unavailable')
        if len(parts)==3 and parts[0]=='evidence':
            token,eid=parts[1],parts[2]
            try:
                row=taskcheck._run_for_token(token); e=taskcheck.db.connect().execute('SELECT * FROM taskcheck_evidence WHERE evidence_id=? AND taskcheck_id=?',(eid,row['taskcheck_id'])).fetchone()
                if not e: raise ValueError('not found')
                p=Path(e['file_path']); data=p.read_bytes(); self.send_response(200); self.send_header('Content-Type',e['mime_type']); self.send_header('Cache-Control','private, no-store'); self.security(); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data); return
            except (ValueError,OSError): return self.error_json(404,'evidence unavailable')
        return self.error_json(404,'not found')
    def read_json(self):
        try: n=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ValueError('invalid content length')
        if n<=0 or n>MAX_JSON: raise ValueError('invalid payload size')
        try: return json.loads(self.rfile.read(n).decode())
        except (UnicodeDecodeError,json.JSONDecodeError): raise ValueError('invalid json')
    def do_POST(self):
        parts=self.token_parts(urlsplit(self.path).path)
        try:
            if len(parts)==4 and parts[:2]==['api','taskcheck'] and parts[3]=='opened':
                return self.json(200,taskcheck.mark_opened(parts[2]))
            if len(parts)==5 and parts[:2]==['api','taskcheck'] and parts[3]=='check':
                data=self.read_json(); result=taskcheck.answer_check(parts[2],parts[4],str(data.get('response','')),str(data.get('note',''))); return self.json(200,{'ok':True,'result':result})
            if len(parts)==5 and parts[:2]==['api','taskcheck'] and parts[3]=='evidence':
                try: n=int(self.headers.get('Content-Length','0'))
                except ValueError: n=0
                if n<=0 or n>MAX_EVIDENCE: raise ValueError('invalid evidence size')
                result=taskcheck.add_evidence(parts[2],parts[4],self.rfile.read(n),self.headers.get('Content-Type','').split(';')[0]); return self.json(201,{'ok':True,'evidence':result})
            if len(parts)==4 and parts[:2]==['api','taskcheck'] and parts[3]=='submit':
                report=taskcheck.complete(parts[2]); notification=notify_requester(report['taskcheck_id']); return self.json(200,{'ok':True,'report':report,'notification':notification})
        except ValueError as e: return self.error_json(400,str(e))
        return self.error_json(404,'not found')

def build_server(host='127.0.0.1',port=8790):
    bootstrap.ensure(); taskcheck.load_builtin_templates(); return ThreadingHTTPServer((host,port),Handler)

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8790); a=p.parse_args(argv); s=build_server(a.host,a.port); print(f'TaskCheck listening on http://{a.host}:{a.port}');
    try: s.serve_forever()
    except KeyboardInterrupt: pass
    finally: s.server_close()
    return 0
if __name__=='__main__': raise SystemExit(main())
