"""Native Nebula UI: local graphics/touch, TLS status polling and owner decisions."""
import json
import os
from pathlib import Path
import queue
import signal
import socket
import ssl
import stat
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
try:  # package import in the LucyOS repo
    from .ui import render, detail_pages
except ImportError:  # flat deployment on the Nebula
    from ui import render, detail_pages

ROOT=Path(__file__).resolve().parent

def solve_calibration(raw):
    targets=[(40,65),(440,65),(240,195)]
    m=[[float(x),float(y),1.,float(tx),float(ty)] for (x,y),(tx,ty) in zip(raw,targets)]
    for col in range(3):
        pivot=max(range(col,3), key=lambda r:abs(m[r][col]))
        m[col],m[pivot]=m[pivot],m[col]
        scale=m[col][col]
        if abs(scale)<1e-7: raise ValueError('Touch points too close')
        m[col]=[v/scale for v in m[col]]
        for row in range(3):
            if row!=col:
                f=m[row][col]; m[row]=[a-f*b for a,b in zip(m[row],m[col])]
    return [[m[i][3] for i in range(3)],[m[i][4] for i in range(3)]]

def map_touch(matrix,x,y):
    return tuple(sum(a*b for a,b in zip(row,(x,y,1))) for row in matrix)

def apply_action(model, action):
    page=model['page']
    if action in ('home','status','inbox'):
        model['page']=action; return None
    if not model.get('online'): return None
    cards=(model.get('data') or {}).get('approvals',[])
    if action=='next' and cards: model['index']=(model.get('index',0)+1)%len(cards)
    elif action=='review':
        if page=='inbox':
            if not cards: return None
            model['selected']=dict(cards[model.get('index',0)%len(cards)]); model['detail']=0
        model['page']='review'
    elif action=='detail_next': model['detail']+=1
    elif action=='review_back':
        if model['detail']>0: model['detail']-=1
        else: model['page']='inbox'
    elif action in ('approve','deny'):
        if page!='review' or model['detail'] != len(detail_pages(model['selected']))-1: return None
        model['decision']='APPROVED' if action=='approve' else 'DENIED'; model['page']='confirm'
    elif action=='send' and page=='confirm':
        chosen=model['selected']
        current=next((c for c in cards if c['approval_id']==chosen['approval_id']),None)
        if current is None or current['revision']!=chosen['revision']:
            model.update(page='result',message='Request changed or resolved. Review the inbox again.'); return None
        model['page']='sending'
        return {'approval_id':chosen['approval_id'],'revision':chosen['revision'],'decision':model['decision']}
    return None

# --- Root-only local remote control (AF_UNIX socket; no network listener) ---
# The socket lives under /run/lucy-nest (root, 0700) and only accepts peer uid 0.
# Decision verbs stay disabled until the root-owned 0600 gate file exists.
CONTROL_SOCK_DIR='/run/lucy-nest'
CONTROL_SOCK=CONTROL_SOCK_DIR+'/control.sock'
REMOTE_DECISIONS_GATE='/root/lucy-nest/native/remote-decisions.enabled'
GATE_MAGIC='ALLOW_REMOTE_DECISIONS'
CONTROL_LINE_LIMIT=256
# Verified against apply_action()/ui.py: none of these submit a decision or put
# anything on the commands queue. 'status' is intercepted by handle_control as a
# snapshot request; the on-screen 'status' page action stays touch-only.
NAV_VERBS=frozenset(('home','status','inbox','next','review','detail_next','review_back'))
# Real existing action names in apply_action(): approve/deny stage on the review
# page, send is the canonical submission that returns the decision command.
DECISION_VERBS=frozenset(('approve','deny','send'))

def parse_control_request(line):
    """Parse one UTF-8 control line (max 256 bytes) -> (verb, arg).

    Raises ValueError on anything that is not a single clean line.
    """
    if isinstance(line,bytes):
        if len(line)>CONTROL_LINE_LIMIT: raise ValueError('request too long')
        try: line=line.decode('utf-8')
        except UnicodeDecodeError: raise ValueError('request must be UTF-8')
    if not isinstance(line,str) or not line or len(line)>CONTROL_LINE_LIMIT:
        raise ValueError('request must be a non-empty line of at most 256 bytes')
    if line.endswith('\n'): line=line[:-1]
    if line.endswith('\r'): line=line[:-1]
    if not line or len(line)>CONTROL_LINE_LIMIT:
        raise ValueError('request must be a non-empty line of at most 256 bytes')
    if any(ch in line for ch in ('\n','\r','\x00')) or line!=line.strip():
        raise ValueError('request must be a single clean line')
    parts=line.split(' ',1)
    verb=parts[0].strip().lower()
    if not verb or not verb.replace('_','').isalnum(): raise ValueError('invalid verb')
    arg=parts[1].strip() if len(parts)>1 else None
    return verb,(arg or None)

def remote_decisions_enabled(path=None):
    """True only when the gate file is a regular non-symlink root-owned 0600
    file whose first line is exactly ALLOW_REMOTE_DECISIONS. Never created here."""
    path=REMOTE_DECISIONS_GATE if path is None else path
    try: st=os.lstat(path)
    except OSError: return False
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode): return False
    if st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600: return False
    try:
        with open(path,'rb') as gate: first=gate.readline(CONTROL_LINE_LIMIT+1)
    except OSError: return False
    return first.rstrip(b'\r\n')==GATE_MAGIC.encode('utf-8')

def _control_peer_uid(conn):
    raw=conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize('3i'))
    _pid,uid,_gid=struct.unpack('3i',raw)
    return uid

def control_server_thread(events,stop,sock_path=CONTROL_SOCK,allowed_uid=0):
    """Serve one-shot root-only control requests over a local AF_UNIX socket.

    Refuses symlinked or non-directory socket dirs, non-socket stale paths and
    peers whose SO_PEERCRED uid differs from allowed_uid. Puts one-shot
    ('control', ev) events with a reply Queue onto the shared events queue and
    never touches the model directly; every error is caught so the display
    thread keeps running.
    """
    srv=None
    try:
        sock_dir=os.path.dirname(sock_path) or '.'
        created=False
        try:
            dir_st=os.lstat(sock_dir)
            if stat.S_ISLNK(dir_st.st_mode) or not stat.S_ISDIR(dir_st.st_mode):
                raise ValueError('control socket dir is not a real directory')
        except FileNotFoundError:
            os.makedirs(sock_dir,0o700); created=True
        if created: os.chmod(sock_dir,0o700)
        try:
            stale=os.lstat(sock_path)
            if stat.S_ISLNK(stale.st_mode): raise ValueError('control socket path is a symlink')
            if stat.S_ISSOCK(stale.st_mode): os.unlink(sock_path)
            else: raise ValueError('control socket path exists and is not a socket')
        except FileNotFoundError: pass
        old_umask=os.umask(0o077)
        try:
            srv=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            srv.bind(sock_path)
        finally:
            os.umask(old_umask)
        os.chmod(sock_path,0o600)
        srv.listen(4)
        srv.settimeout(0.2)
        while not stop.is_set():
            try: conn,_addr=srv.accept()
            except socket.timeout: continue
            try:
                conn.settimeout(2.0)
                if _control_peer_uid(conn)!=allowed_uid:
                    reply={'ok':False,'error':'refused: peer uid not allowed'}
                else:
                    data=conn.recv(CONTROL_LINE_LIMIT)
                    try: verb,arg=parse_control_request(data)
                    except ValueError as error: reply={'ok':False,'error':'bad request: '+str(error)}
                    else:
                        ev={'verb':verb,'arg':arg,'reply':queue.Queue()}
                        events.put(('control',ev))
                        try: reply=ev['reply'].get(timeout=2.0)
                        except queue.Empty: reply={'ok':False,'error':'control handler timed out'}
                conn.sendall((json.dumps(reply)+'\n').encode('utf-8'))
            except Exception:
                try: conn.sendall(b'{"ok":false,"error":"control error"}\n')
                except OSError: pass
            finally: conn.close()
    except Exception as error:
        events.put(('control_error',type(error).__name__+': '+str(error)))
    finally:
        if srv is not None:
            try: srv.close()
            except OSError: pass
        try:
            if stat.S_ISSOCK(os.lstat(sock_path).st_mode): os.unlink(sock_path)
        except OSError: pass

def _control_snapshot(model):
    cards=(model.get('data') or {}).get('approvals',[])
    index=model.get('index',0)
    focused=cards[index%len(cards)] if cards else None
    def short(value):
        value=str(value or '')
        return value[:80]
    return {
        'ok':True,
        'page':model.get('page'),
        'index':index,
        'approvals':len(cards),
        'focused_id':short(focused.get('approval_id')) if focused else None,
        'focused_title':short(focused.get('action')) if focused else None,
        'online':bool(model.get('online')),
        'last_update':model.get('updated'),
        'touch':model.get('touch_status','unknown'),
        'remote_decisions':remote_decisions_enabled(),
    }

def _shown_matches_pending(model):
    """True when the shown selection still matches a pending approval (id+revision)."""
    shown=model.get('selected')
    if not isinstance(shown,dict): return False
    for pending in (model.get('data') or {}).get('approvals',[]):
        if pending.get('approval_id')==shown.get('approval_id') and pending.get('revision')==shown.get('revision'):
            return True
    return False

def handle_control(model,ev):
    """Run one parsed control request against the model (main loop only).

    Returns a decision command for the existing commands queue, or None. Nav
    verbs never submit; decision verbs re-check the gate and require the shown
    item to match the currently pending approval before using apply_action().
    """
    verb=ev.get('verb'); command=None
    if verb=='status': reply=_control_snapshot(model)
    elif verb in NAV_VERBS:
        if apply_action(model,verb) is not None:
            reply={'ok':False,'error':'refused: navigation never submits'}
        else: reply={'ok':True,'page':model.get('page')}
    elif verb in DECISION_VERBS:
        if not remote_decisions_enabled(): reply={'ok':False,'error':'refused: remote decisions disabled'}
        elif not _shown_matches_pending(model): reply={'ok':False,'error':'refused: no matching pending approval'}
        else:
            command=apply_action(model,verb)
            reply={'ok':True,'page':model.get('page')}
    else: reply={'ok':False,'error':'unknown verb'}
    ev['reply'].put(reply)
    return command

def validate_connection_config(config):
    if not isinstance(config, dict):
        raise ValueError('Connection config must be an object')
    url = config.get('url')
    token = config.get('token')
    parsed = urlparse(str(url or ''))
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Lucy-Nest connection must use a credential-free HTTPS URL')
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError('Lucy-Nest connection has an invalid port') from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('Lucy-Nest connection has an invalid port')
    if not isinstance(token, str) or not token.strip():
        raise ValueError('Lucy-Nest connection auth value is empty')
    return str(url), token.strip()


def validate_status(payload):
    required = {'as_of', 'source', 'counts', 'active', 'approvals', 'paused', 'safe_mode'}
    if not isinstance(payload, dict) or not required.issubset(payload):
        raise ValueError('Invalid Lucy-Nest status shape')
    if payload['source'] != 'LucyOS / this laptop':
        raise ValueError('Unexpected Lucy-Nest status source')
    if isinstance(payload['as_of'], bool) or not isinstance(payload['as_of'], (int, float)):
        raise ValueError('Invalid Lucy-Nest status timestamp')
    if not isinstance(payload['counts'], dict) or not isinstance(payload['active'], list) or not isinstance(payload['approvals'], list):
        raise ValueError('Invalid Lucy-Nest status collections')
    return payload


def require_device_runtime():
    if os.environ.get('LUCY_NEST_RUNTIME') != 'nebula' or os.environ.get('LUCY_NEST_DISPLAY_OWNER') != 'confirmed':
        raise SystemExit('Lucy-Nest native execution is disabled until device runtime and display ownership are explicit')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Connection:
    def __init__(self):
        cfg=json.loads((ROOT/'connection.json').read_text())
        self.url, self.token = validate_connection_config(cfg)
        self.ctx=ssl.create_default_context(cafile=str(ROOT/'server.crt'))
        self.opener=urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=self.ctx))
    def request(self,path,body=None):
        request=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        with self.opener.open(request,timeout=4) as response:
            return json.loads(response.read(200000))

class TouchDecoder:
    """Decode single-touch evdev events without assuming SYN ordering.

    The NS2009 reports BTN_TOUCH, but its coordinate/SYN ordering can vary
    after boot. Keeping this logic pure makes the hardware path testable and
    lets the client accept both legacy ABS_X/Y and MT position codes.
    """
    EV_SYN = 0
    EV_KEY = 1
    EV_ABS = 3
    SYN_REPORT = 0
    BTN_TOUCH = 330
    ABS_X = 0
    ABS_Y = 1
    ABS_MT_POSITION_X = 53
    ABS_MT_POSITION_Y = 54

    def __init__(self):
        self.x = None
        self.y = None
        self.down = False
        self.start = None
        self.last_emit = 0.0

    def _point(self):
        if self.x is None or self.y is None:
            return None
        return (self.x, self.y)

    def feed(self, kind, code, value, now=None):
        now = time.monotonic() if now is None else now
        if kind == self.EV_ABS:
            if code in (self.ABS_X, self.ABS_MT_POSITION_X):
                self.x = value
            elif code in (self.ABS_Y, self.ABS_MT_POSITION_Y):
                self.y = value
            if self.down and self.start is None:
                self.start = self._point()
        elif kind == self.EV_KEY and code == self.BTN_TOUCH:
            if value:
                self.down = True
                self.start = self._point()
            elif self.down:
                self.down = False
                start = self.start
                end = self._point() or start
                self.start = None
                self.x = self.y = None
                if start is not None and end is not None and now - self.last_emit >= 0.35:
                    self.last_emit = now
                    return (start, end)
        elif kind == self.EV_SYN and code == self.SYN_REPORT and self.down and self.start is None:
            self.start = self._point()
        return None


def touch(events):
    try:
        fmt = 'llHHi'
        size = struct.calcsize(fmt)
        decoder = TouchDecoder()
        with open('/dev/input/event0', 'rb', buffering=0) as stream:
            while True:
                data = stream.read(size)
                if len(data) != size:
                    raise RuntimeError('Touch input closed')
                _, _, kind, code, value = struct.unpack(fmt, data)
                point = decoder.feed(kind, code, value)
                if point is not None:
                    events.put(('touch', point))
    except Exception as error:
        events.put(('touch_error', type(error).__name__))

def network(events,commands):
    conn=Connection()
    while True:
        try:
            command=commands.get_nowait()
        except queue.Empty: command=None
        if command:
            try:
                result=conn.request('/decision',command)
                message='LucyOS confirmed: '+str(result['status'])+'.'
                if result['status']=='APPROVED':
                    message += (' The linked task is released; completion is tracked separately.'
                                if result.get('task_id') else
                                ' No linked task was reported; completion is not implied.')
                events.put(('result',message))
            except urllib.error.HTTPError as error:
                try: message=json.loads(error.read(4096)).get('error','Decision not confirmed.')
                except Exception: message='Decision not confirmed.'
                events.put(('result',message))
            except Exception:
                events.put(('result','Connection interrupted. Decision outcome unknown. Refresh the inbox; do not assume it failed.'))
        try:
            events.put(('status', validate_status(conn.request('/status'))))
        except Exception:
            events.put(('offline',None))
        time.sleep(1)

def main():
    require_device_runtime()
    events=queue.Queue(); commands=queue.Queue(); control_stop=threading.Event()
    model={'page':'home','online':False,'data':{},'index':0}; matrix=None; raw=[]; tick=0; updated=0
    try: matrix=json.loads((ROOT/'calibration.json').read_text())
    except (OSError,ValueError): model.update(page='calibrate',cal_step=0)
    threading.Thread(target=touch,args=(events,),daemon=True).start()
    threading.Thread(target=network,args=(events,commands),daemon=True).start()
    threading.Thread(target=control_server_thread,args=(events,control_stop),daemon=True).start()
    def _request_stop(*_args):
        control_stop.set(); raise SystemExit
    for sig in (signal.SIGINT,signal.SIGTERM):
        try: signal.signal(sig,_request_stop)
        except (ValueError,OSError): pass
    try:
        hits=[]
        while True:
            began=time.monotonic()
            while True:
                try: kind,value=events.get_nowait()
                except queue.Empty: break
                if kind=='status':
                    model.update(data=value,online=True); updated=time.monotonic(); model['updated']=time.time()
                elif kind=='offline': model['online']=False
                elif kind=='result': model.update(page='result',message=value)
                elif kind=='touch_error':
                    model.update(page='result',message='Touch input unavailable: '+value); model['touch_status']='error: '+value
                elif kind=='control_error':
                    print('Remote control unavailable: '+str(value),flush=True)
                elif kind=='control':
                    try:
                        command=handle_control(model,value)
                    except Exception:
                        value['reply'].put({'ok':False,'error':'control error'}); command=None
                    if command: commands.put(command)
                elif kind=='touch':
                    model['touch_status']='ok'
                    start,end=value
                    if model['page']=='calibrate':
                        raw.append(end)
                        if len(raw)==3:
                            try:
                                matrix=solve_calibration(raw)
                                (ROOT/'calibration.json').write_text(json.dumps(matrix)); model['page']='home'
                                print('Touch calibration saved',flush=True)
                            except ValueError: raw=[]; model['cal_step']=0
                        else: model['cal_step']=len(raw)
                    elif matrix is not None:
                        p1=map_touch(matrix,*start); p2=map_touch(matrix,*end)
                        for (left,top,right,bottom),action in hits:
                            if all(left<=p[0]<=right and top<=p[1]<=bottom for p in (p1,p2)):
                                command=apply_action(model,action)
                                if command: commands.put(command)
                                print('Touch: '+action+' -> '+model['page'],flush=True)
                                break
        if time.monotonic()-updated>6: model['online']=False
        image,hits=render(model,tick)
        image.save('/tmp/lucy-native.jpg','JPEG',quality=87)
        subprocess.run(['/usr/bin/cmd_jpeg_display','/tmp/lucy-native.jpg'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3,check=True)
        tick+=1
        interval=.08 if model['page']=='home' else .20
        time.sleep(max(.01,interval-(time.monotonic()-began)))
    finally:
        control_stop.set()

if __name__=='__main__': main()
