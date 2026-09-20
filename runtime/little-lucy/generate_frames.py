from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

W,H=480,272
BG=(9,10,9); WHITE=(242,239,230); DIM=(112,112,108); RED=(227,58,53); GRID=(38,38,38)
ROOT=Path(__file__).parent/'frames'
STATES=['ready','thinking','working','verify','success','needs_you','offline']
FRAMES=18

def font(size,bold=False):
    paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
           '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for p in paths:
        try:return ImageFont.truetype(p,size)
        except:pass
    return ImageFont.load_default()

F_BIG=font(22,True); F_SMALL=font(11,True); F_TINY=font(9,True)

def center_text(d,y,text,f,fill):
    b=d.textbbox((0,0),text,font=f); x=(W-(b[2]-b[0]))//2; d.text((x,y),text,font=f,fill=fill)

def eye_geometry(d,t,state):
    cx,cy=240,119
    open_amt=1.0
    if state=='ready': open_amt=.88 + .08*math.sin(t*2*math.pi)
    elif state=='thinking': open_amt=.82 + .12*math.sin(t*4*math.pi)
    elif state=='working': open_amt=.92 + .04*math.sin(t*6*math.pi)
    elif state=='verify': open_amt=.60 + .05*math.sin(t*2*math.pi)
    elif state=='success': open_amt=1.0
    elif state=='needs_you': open_amt=.95
    elif state=='offline': open_amt=.12
    # occasional blink for calm states
    if state in ('ready','thinking') and 0.46<t<0.52: open_amt=.12
    ew,eh=292,int(92*open_amt)
    left,top,right,bottom=cx-ew//2,cy-eh//2,cx+ew//2,cy+eh//2
    if state=='offline':
        d.line((cx-110,cy,cx+110,cy),fill=DIM,width=5)
        return
    # aperture shell, layered to retain hand-sketched rib language
    d.rounded_rectangle((left,top,right,bottom),radius=max(12,eh//2),outline=WHITE,width=4)
    for off in (11,22):
        if eh>40:
            d.arc((left+off,top+off//3,right-off,bottom-off//3),180,360,fill=(175,175,169),width=1)
            d.arc((left+off,top+off//3,right-off,bottom-off//3),0,180,fill=(175,175,169),width=1)
    # side ribs
    for side in (-1,1):
        base=cx+side*(ew//2+4)
        for i in range(5):
            yy=cy-32+i*16
            length=18-(abs(2-i)*3)
            x2=base+side*length
            d.line((base,yy,x2,yy),fill=(130,130,125),width=2)
    # pupils
    if state=='thinking': gaze=math.sin(t*2*math.pi)*22
    elif state=='working': gaze=math.sin(t*4*math.pi)*8
    elif state=='verify': gaze=10*math.sin(t*6*math.pi)
    else: gaze=0
    sep=48
    py=cy+int(2*math.sin(t*2*math.pi))
    for px in (cx-sep+gaze,cx+sep+gaze):
        d.ellipse((px-13,py-13,px+13,py+13),outline=WHITE,width=3)
        d.ellipse((px-4,py-4,px+4,py+4),fill=WHITE)
    if state=='verify':
        scanx=int(left+16+(ew-32)*t)
        d.line((scanx,top+12,scanx,bottom-12),fill=RED,width=2)
    if state=='working':
        # evidence/activity bars: only white/gray; red reserved for labels
        for i in range(8):
            x=158+i*23; y=185
            active=i <= int(t*7)
            d.rounded_rectangle((x,y,x+14,y+5),radius=2,fill=WHITE if active else GRID)
    if state=='success':
        d.arc((cx-70,cy+20,cx+70,cy+68),0,180,fill=WHITE,width=3)

def make(state,i):
    t=i/(FRAMES-1)
    im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
    # top framing
    d.text((18,16),'LUCY-NEST',font=F_SMALL,fill=WHITE)
    d.text((382,16),'LIVE',font=F_SMALL,fill=RED if state in ('working','verify','needs_you') else DIM)
    d.line((18,38,462,38),fill=GRID,width=1)
    eye_geometry(d,t,state)
    labels={
        'ready':('READY','SYSTEM ONLINE',WHITE),
        'thinking':('THINKING','FORMING NEXT ACTION',WHITE),
        'working':('WORKING','EXECUTING VERIFIED PLAN',RED),
        'verify':('VERIFYING','CHECKING EVIDENCE',RED),
        'success':('VERIFIED','PASSING ARTIFACTS CONFIRMED',WHITE),
        'needs_you':('NEEDS YOU','OWNER INPUT REQUIRED',RED),
        'offline':('OFFLINE','RECONNECTING TO LUCYOS',RED),
    }
    title,detail,color=labels[state]
    center_text(d,211,title,F_BIG,color)
    center_text(d,242,detail,F_TINY,DIM if state!='needs_you' else WHITE)
    # bottom signal / heartbeat
    d.line((18,261,462,261),fill=GRID,width=1)
    pulse=18+int(22*(0.5+0.5*math.sin(t*2*math.pi)))
    d.line((18,261,18+pulse,261),fill=RED if state in ('working','verify','needs_you') else WHITE,width=2)
    return im

def main():
    for state in STATES:
        out=ROOT/state; out.mkdir(parents=True,exist_ok=True)
        for i in range(FRAMES):
            make(state,i).save(out/f'{i:02d}.jpg',quality=94,subsampling=0)
    make('ready',0).save(Path(__file__).parent/'current.jpg',quality=94,subsampling=0)
    print(f'generated {len(STATES)*FRAMES} frames at {W}x{H}')

if __name__=='__main__': main()
