"""Original pixel pig + shared timeline rendered using native SVG SMIL only."""
import argparse
import datetime as dt
from html import escape
import json
from pathlib import Path
from contributions import fetch, validate

ROOT = Path(__file__).resolve().parents[1]
PITCH, X0, Y0 = 16, 34, 43
PALETTES = {
    'light': dict(bg='#fffaf4', text='#8b747b', grid=['#efe9e3','#d9eadb','#b9d6c3','#dfadb9','#bd7b91']),
    'dark': dict(bg='#211e27', text='#bcaab9', grid=['#35303d','#415b50','#688975','#aa7b91','#dba7b6'])}


def sprite(direction='right', eating=False):
    """16x16 pixel silhouette, drawn by hand. Facing is anatomical, not rotated."""
    parts = []
    def rect(x,y,w,h,c):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>')
    outline, pink, light, rose, eye = '#ac607a','#f3adc2','#ffd0da','#db859f','#593d55'
    # Stepped outline and round body.
    for x,y,w,h in [(3,5,10,8),(2,7,12,4),(5,4,6,10)]: rect(x,y,w,h,outline)
    for x,y,w,h in [(4,5,8,8),(3,7,10,4),(5,5,5,8)]: rect(x,y,w,h,pink)
    rect(5,6,6,2,light)
    rect(4,12,2,2,outline); rect(10,12,2,2,outline)
    if direction in ('left','right'):
        rect(5,2,3,4,outline); rect(6,3,2,3,pink); rect(6,4,1,2,rose)
        rect(10,3,2,3,outline); rect(10,4,1,2,pink)
        # A one-pixel curly tail on the rump.
        for x,y in [(2,8),(1,8),(0,7),(0,6),(1,5),(2,5),(2,6)]: rect(x,y,1,1,outline)
        rect(11,8,5,4,outline); rect(12,8,4,3,rose)
        rect(13,9,1,1,outline); rect(15,9,1,1,outline)
        if eating:
            rect(10,7,2,1,eye); rect(9,8,1,1,eye); rect(12,12,2,1,eye)
        else: rect(10,7,1,2,eye)
        rect(9,10,2,1,rose)
    else:
        rect(3,2,3,4,outline); rect(10,2,3,4,outline)
        rect(4,3,2,3,pink); rect(10,3,2,3,pink)
        if direction == 'down':
            for x in (5,10): rect(x,7,2 if eating else 1,1 if eating else 2,eye)
            rect(6,9,5,3,rose); rect(7,10,1,1,outline); rect(9,10,1,1,outline)
            rect(4,10,1,1,rose); rect(12,10,1,1,rose)
        else:
            rect(7,10,2,1,outline); rect(8,9,2,1,outline); rect(9,10,1,2,outline); rect(7,12,2,1,outline)
    body = ''.join(parts)
    if direction == 'left': body = f'<g transform="translate(16 0) scale(-1 1)">{body}</g>'
    return body


def plan(days):
    """Nearest snack first; adjacent grid steps, no snake body constraints."""
    cells = {(d['x'],d['y']): d for d in days}
    snacks = {p for p,d in cells.items() if d['level']}
    start = min(cells)
    pos, facing, t = start, 'right', 0.0
    frames = [(t, *pos, facing, False, 1.0, 1.0, 0)]
    eaten = {}
    def frame(delay, p, direction, eat=False, sx=1., sy=1., bounce=0):
        nonlocal t
        t += delay
        frames.append((round(t,5), *p, direction, eat, sx, sy, bounce))
    def nibble():
        if pos in snacks:
            frame(.10,pos,facing,True,1.12,.86,1)
            eaten[pos] = t
            frame(.16,pos,facing,True,.94,1.06,-1)
            frame(.18,pos,facing)
            snacks.remove(pos)
    def walk(target):
        nonlocal pos, facing
        while pos != target:
            dx,dy = target[0]-pos[0], target[1]-pos[1]
            # Prefer a snack directly ahead, then follow the longer axis.
            options = []
            if dx: options.append((pos[0]+(1 if dx>0 else -1),pos[1]))
            if dy: options.append((pos[0],pos[1]+(1 if dy>0 else -1)))
            nxt = min(options, key=lambda p:(p not in snacks, p not in cells, abs(target[0]-p[0])+abs(target[1]-p[1]), p))
            facing = 'right' if nxt[0]>pos[0] else 'left' if nxt[0]<pos[0] else 'down' if nxt[1]>pos[1] else 'up'
            # Turn in place, then a lifted mid-step and soft landing.
            frame(.001,pos,facing)
            mid = ((pos[0]+nxt[0])/2,(pos[1]+nxt[1])/2)
            frame(.11,mid,facing,bounce=-1.6)
            frame(.11,nxt,facing)
            pos = nxt
            nibble()
    frame(.65,pos,facing)
    nibble()
    while snacks:
        target = min(snacks,key=lambda p:(abs(p[0]-pos[0])+abs(p[1]-pos[1]), -cells[p]['level'], p))
        walk(target)
    frame(.6,pos,facing)
    walk(start)
    frame(.001,start,'right')
    frame(.7,start,'right')
    # Reset happens while the pig is stationary. All clocks share this duration.
    frame(.6,start,'right')
    return frames, eaten, t


def render(data, theme, frames, eaten, duration):
    days = data['days']; colors = PALETTES[theme]
    width, height = X0 + (max(d['x'] for d in days)+1)*PITCH + 14, 178
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           '<title id="title">Chloe’s contribution piggy</title>',
           f'<desc id="desc">A tiny pink pig eats {sum(d["level"]>0 for d in days)} contribution squares from {days[0]["date"]} to {days[-1]["date"]}, then the garden regrows. Data: GitHub.</desc>',
           f'<rect width="{width}" height="{height}" rx="12" fill="{colors["bg"]}"/>',
           f'<g fill="{colors["text"]}" font-family="ui-monospace,monospace" font-size="9">']
    last_month = None
    month_starts = []
    for d in days:
        month = d['date'][:7]
        if month != last_month:
            month_starts.append(d)
            last_month=month
    for i, d in enumerate(month_starts):
        next_x = month_starts[i+1]['x'] if i+1 < len(month_starts) else max(x['x'] for x in days)+1
        if next_x-d['x'] >= 3:
            label = dt.date.fromisoformat(d['date']).strftime('%b')
            out.append(f'<text x="{X0+d["x"]*PITCH-5}" y="22">{label}</text>')
    for y,label in [(1,'M'),(3,'W'),(5,'F')]: out.append(f'<text x="13" y="{Y0+y*PITCH+3}">{label}</text>')
    out.append('</g>')
    for d in days:
        p=(d['x'],d['y']); x=X0+p[0]*PITCH-5; y=Y0+p[1]*PITCH-5
        out.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{colors["grid"][0]}"/>')
        if d['level']:
            when=eaten[p]/duration; reset=(duration-.6)/duration
            out.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{colors["grid"][d["level"]]}"><animate attributeName="opacity" values="1;0;0;1;1" keyTimes="0;{when:.8f};{reset:.8f};{(duration-.2)/duration:.8f};1" calcMode="discrete" dur="{duration:.5f}s" repeatCount="indefinite"/></rect>')
    times=';'.join(f'{f[0]/duration:.8f}' for f in frames)
    def animate(attr,values,kind=None,discrete=False):
        tag='animateTransform' if kind else 'animate'
        typeattr=f' type="{kind}"' if kind else ''
        return f'<{tag} attributeName="{attr}"{typeattr} values="{";".join(values)}" keyTimes="{times}" dur="{duration:.5f}s" repeatCount="indefinite" calcMode="{"discrete" if discrete else "linear"}"/>'
    out.append(f'<g transform="translate({X0+frames[0][1]*PITCH} {Y0+frames[0][2]*PITCH})">')
    out.append(animate('transform',[f'{X0+f[1]*PITCH:.2f} {Y0+f[2]*PITCH+f[7]:.2f}' for f in frames],'translate'))
    out.append('<g>'); out.append(animate('transform',[f'{f[5]} {f[6]}' for f in frames],'scale'))
    for direction in ('right','left','up','down'):
        for eating in (False,True):
            active = direction=='right' and not eating
            out.append(f'<g opacity="{int(active)}">')
            out.append(animate('opacity',[str(int(f[3]==direction and f[4]==eating)) for f in frames],discrete=True))
            out.append(f'<g transform="translate(-10 -10) scale(1.25)" shape-rendering="crispEdges">{sprite(direction,eating)}</g></g>')
    out.append('</g></g></svg>')
    return ''.join(out)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--username',default='chloezqy'); ap.add_argument('--data',type=Path)
    ap.add_argument('--output',type=Path,default=ROOT/'dist')
    args=ap.parse_args()
    data=json.loads(args.data.read_text()) if args.data else fetch(args.username)
    data['days']=validate(data['days'])
    frames,eaten,duration=plan(data['days'])
    args.output.mkdir(parents=True,exist_ok=True)
    for theme in PALETTES:
        (args.output/f'piggy-{theme}.svg').write_text(render(data,theme,frames,eaten,duration))
    (args.output/'contributions.json').write_text(json.dumps(data,indent=2)+'\n')
    for direction in ('right','left','up','down'):
        (ROOT/'assets'/f'piggy-{direction}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 0 18 16" width="144" height="128" shape-rendering="crispEdges">{sprite(direction)}</svg>')
    print(f'{len(data["days"])} real days · {len(eaten)} snacks · {duration:.1f}s loop · {len(frames)} keyframes')

if __name__=='__main__': main()
