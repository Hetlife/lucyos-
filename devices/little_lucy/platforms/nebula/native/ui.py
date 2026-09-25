"""480x272 native Nest UI. Runs entirely on the Nebula with Pillow."""
import math
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
WHITE='#f2efe6'; DIM='#aaaaa5'; RED='#e33a35'; GREEN='#b8e6b8'
FONTS={}
def font(size):
    if size not in FONTS: FONTS[size]=ImageFont.truetype(str(ROOT/'font.ttf'),size)
    return FONTS[size]

def text_width(text, size):
    f=font(size)
    return f.getlength(text) if hasattr(f,'getlength') else f.getsize(text)[0]

@lru_cache(maxsize=256)
def wrap(text, width=440, size=15):
    d=ImageDraw.Draw(Image.new('RGB',(1,1)))
    lines=[]; current=''
    for char in ' '.join(str(text).split()):
        if text_width(current+char,size) > width:
            lines.append(current); current=''
        current+=char
    if current: lines.append(current)
    return lines or ['Not specified']

def detail_pages(card):
    lines=[]
    for label,key in [('ACTION','action'),('WHY','why'),('COST','cost'),('DOWNSIDE','max_downside'),('BENEFIT','expected_benefit'),('REVERSIBLE','reversibility'),('RESUMES','resumes')]:
        lines.extend(wrap(label+': '+card.get(key,'Not specified')))
    return [lines[i:i+7] for i in range(0,len(lines),7)]

def render(model, tick=0):
    im=Image.new('RGB',(480,272),'#090a09'); d=ImageDraw.Draw(im); hits=[]
    def text(x,y,t,size=16,color=WHITE): d.text((x,y),str(t),font=font(size),fill=color)
    def line(y,t,size=16,color=WHITE): text(18,y,wrap(t,444,size)[0],size,color)
    def button(x,w,label,action,color=WHITE):
        box=(x,222,x+w,268); d.rectangle(box,outline=color,width=2)
        tw=text_width(label,16); text(x+(w-tw)//2,235,label,16,color); hits.append((box,action))
    page=model.get('page','home'); data=model.get('data') or {}; online=model.get('online',False)
    line(9,'LUCY NEST' if page=='home' else 'LUCY NEST / '+page.upper(),17)
    text(374,12,'ONLINE' if online else 'OFFLINE',13,GREEN if online else RED)
    d.line((18,36,462,36),fill='#393939')
    if page=='calibrate':
        points=[(40,65),(440,65),(240,195)]; x,y=points[model.get('cal_step',0)]
        line(40,'Touch the cross: %s of 3' % (model.get('cal_step',0)+1),16)
        d.line((x-12,y,x+12,y),fill=RED,width=3); d.line((x,y-12,x,y+12),fill=RED,width=3)
        line(241,'One-time touchscreen setup',14,DIM)
    elif page=='home':
        # Reference-inspired red field and black almond eye; drawn on-device.
        red='#f20710'; ink='#100706'
        d.rectangle((0,0,479,271),fill=red)
        text(18,12,'LUCY NEST',15,ink)
        text(374,14,'ONLINE' if online else 'OFFLINE',12,ink)
        phase=(tick % 90)/12.5
        # A smooth glance with a brief asymmetric blink every 7.2 seconds.
        gaze=math.sin(phase*math.pi/3.6)*40
        blink=max(0.0,1.0-abs(phase-4.4)/0.20)
        opening=1.0-0.96*blink
        cx=240; cy=120+2*math.sin(phase*math.pi/3.6)
        half_width=174; half_height=49*opening
        upper=[]; lower=[]
        for i in range(65):
            u=i/64; x=cx-half_width+2*half_width*u
            curve=math.sin(math.pi*u)**0.85
            tilt=(u-.5)*8
            upper.append((x,cy-half_height*curve+tilt))
            lower.append((x,cy+half_height*.88*curve+tilt))
        d.polygon(upper+list(reversed(lower)),fill=ink)
        if opening>.2:
            px=cx+gaze; py=cy-15; radius=33
            d.ellipse((px-radius,py-radius,px+radius,py+radius),fill=red)
        n=len(data.get('approvals',[]))
        label='NEEDS HET' if online and n else ('READY' if online else 'RECONNECTING')
        tw=text_width(label,23); text((480-tw)//2,196,label,23,ink)
        caption=('%s request(s) for you — tap to view' % n) if online and n else ('Tap Ready for status' if online else 'Local display running')
        tw=text_width(caption,13); text((480-tw)//2,237,caption,13,ink)
        hits.append(((0,38,479,271),'status'))
    elif page=='status':
        counts=data.get('counts',{}); done=counts.get('DONE',0); total=sum(v for k,v in counts.items() if k!='CANCELLED')
        line(47,'LucyOS: connected' if online else 'LucyOS: disconnected / showing last update',15,GREEN if online else RED)
        line(72,('Completed: %s / %s tasks' % (done,total)) if total else 'No tasks in laptop LucyOS',19)
        active=data.get('active',[])
        line(101,'Now: '+(active[0]['title'] if active else 'No running task recorded'),15)
        line(126,'Blocked: %s   Ready: %s' % (counts.get('BLOCKED',0),counts.get('READY',0)),15)
        flags='PAUSED' if data.get('paused') else ('SAFE MODE' if data.get('safe_mode') else 'Laptop task state')
        line(151,flags,14,DIM)
        line(177,'For Het: %s pending request(s)' % len(data.get('approvals',[])),16)
        line(201,'Task update: '+str(data.get('last_task_update') or 'none'),11,DIM)
        button(10,140,'Eyes','home'); button(165,305,'Het inbox','inbox')
    elif page=='inbox':
        cards=data.get('approvals',[])
        if not online: line(63,'Reconnect to review or decide.',17,RED)
        elif not cards: line(63,'No pending requests for Het.',18)
        else:
            idx=model.get('index',0)%len(cards); c=cards[idx]
            line(48,'%s  /  %s of %s' % (c['approval_id'],idx+1,len(cards)),16)
            for i,t in enumerate(wrap(c['action'])[:5]): line(78+23*i,t,15)
            button(165,140,'Next','next'); button(320,150,'Review','review')
        button(10,140,'Back','status')
    elif page=='review':
        c=model['selected']; pages=detail_pages(c); idx=model.get('detail',0)
        line(45,'%s / details %s of %s' % (c['approval_id'],idx+1,len(pages)),14,DIM)
        for i,t in enumerate(pages[idx]): line(68+i*20,t,15)
        button(10,125,'Back','review_back')
        if idx<len(pages)-1: button(150,320,'Read next','detail_next')
        else:
            button(150,150,'Reject','deny',RED); button(315,155,'Approve','approve',GREEN)
    elif page=='confirm':
        decision=model['decision']; c=model['selected']
        line(55,('Approve ' if decision=='APPROVED' else 'Reject ')+c['approval_id']+'?',22)
        for i,t in enumerate(wrap(c['action'])[:3]): line(92+22*i,t,15)
        line(171,'Sends your decision to LucyOS.',15,DIM)
        button(10,215,'Go back','review'); button(240,230,'Yes, send','send',GREEN if decision=='APPROVED' else RED)
    elif page=='sending':
        line(83,'Sending decision...',22); line(124,'Waiting for LucyOS acknowledgement.',15,DIM)
    elif page=='result':
        for i,t in enumerate(wrap(model.get('message',''),440,18)[:6]): line(55+i*25,t,18)
        button(10,460,'Return to status','status')
    return im,hits
