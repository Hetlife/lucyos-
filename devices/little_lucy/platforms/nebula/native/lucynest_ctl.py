#!/usr/bin/env python3
"""Root-only local control client for the Nebula native remote-control socket.

Run as root on the Nebula: ``python3 lucynest_ctl.py status`` (or a navigation
verb such as ``inbox`` / ``next``). Decision verbs (approve/deny/send) are
refused unless the root-owned 0600 gate file is enabled on the device. This
client is stdlib-only, never imports client.py, and never opens a network
connection: it only talks to the local AF_UNIX control socket.

Exit codes: 0 ok, 1 refused (not root, bad verb, or server refused),
2 unreachable (socket missing, connect/timeout/protocol failure).
"""
import json
import os
import socket
import sys

CONTROL_SOCK='/run/lucy-nest/control.sock'
CONTROL_LINE_LIMIT=256
CONNECT_TIMEOUT=5.0
# Mirrors client.py NAV_VERBS + DECISION_VERBS; duplicated so this file never
# imports client.py on the flat device layout.
NAV_VERBS=frozenset(('home','status','inbox','next','review','detail_next','review_back'))
SNAPSHOT_VERBS=frozenset(('info',))
DECISION_VERBS=frozenset(('approve','deny','send'))
KNOWN_VERBS=NAV_VERBS|SNAPSHOT_VERBS|DECISION_VERBS

def build_request(verb,arg=None):
    """Build the one-line request payload bytes; raises ValueError when invalid."""
    verb=str(verb or '').strip().lower()
    if not verb or not verb.replace('_','').isalnum():
        raise ValueError('invalid verb')
    if verb not in KNOWN_VERBS:
        raise ValueError('unknown verb: '+verb)
    line=verb if arg is None else verb+' '+str(arg).strip()
    if any(ch in line for ch in ('\n','\r','\x00')) or line!=line.strip():
        raise ValueError('request must be a single clean line')
    if len(line.encode('utf-8'))>CONTROL_LINE_LIMIT:
        raise ValueError('request too long')
    return (line+'\n').encode('utf-8')

def run(argv,sock_path=CONTROL_SOCK):
    """Run one control request; returns the process exit code."""
    if os.geteuid()!=0:
        print(json.dumps({'ok':False,'error':'refused: lucynest_ctl must run as root'}))
        return 1
    if not argv or len(argv)>2:
        print(json.dumps({'ok':False,'error':'usage: lucynest_ctl VERB [ARG]'}))
        return 1
    try: payload=build_request(argv[0],argv[1] if len(argv)>1 else None)
    except ValueError as error:
        print(json.dumps({'ok':False,'error':'refused: '+str(error)}))
        return 1
    buf=b''
    try:
        sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            sock.settimeout(CONNECT_TIMEOUT)
            sock.connect(sock_path)
            sock.sendall(payload)
            while b'\n' not in buf and len(buf)<=4096:
                chunk=sock.recv(1024)
                if not chunk: break
                buf+=chunk
        finally:
            sock.close()
    except OSError:
        print(json.dumps({'ok':False,'error':'unreachable: control socket'}))
        return 2
    line=buf.split(b'\n',1)[0].decode('utf-8','replace')
    try: reply=json.loads(line)
    except ValueError: reply={'ok':False,'error':'bad reply from control socket'}
    print(json.dumps(reply))
    return 0 if reply.get('ok') else 1

def main():
    sys.exit(run(sys.argv[1:]))

if __name__=='__main__':
    main()
