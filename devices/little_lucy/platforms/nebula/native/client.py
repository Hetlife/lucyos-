"""Native Nebula UI: local graphics/touch, TLS status polling and owner decisions."""
import json
import os
from pathlib import Path
import queue
import ssl
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
    events=queue.Queue(); commands=queue.Queue()
    model={'page':'home','online':False,'data':{},'index':0}; matrix=None; raw=[]; tick=0; updated=0
    try: matrix=json.loads((ROOT/'calibration.json').read_text())
    except (OSError,ValueError): model.update(page='calibrate',cal_step=0)
    threading.Thread(target=touch,args=(events,),daemon=True).start()
    threading.Thread(target=network,args=(events,commands),daemon=True).start()
    hits=[]
    while True:
        began=time.monotonic()
        while True:
            try: kind,value=events.get_nowait()
            except queue.Empty: break
            if kind=='status':
                model.update(data=value,online=True); updated=time.monotonic()
            elif kind=='offline': model['online']=False
            elif kind=='result': model.update(page='result',message=value)
            elif kind=='touch_error':
                model.update(page='result',message='Touch input unavailable: '+value)
            elif kind=='touch':
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

if __name__=='__main__': main()
