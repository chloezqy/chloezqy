"""Optional development-only browser validation; requires Playwright + Chromium."""
import argparse
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from piggy import plan

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--chrome',help='Optional installed Chrome executable')
args=p.parse_args()
with sync_playwright() as pw:
    browser=pw.chromium.launch(**({'executable_path':args.chrome} if args.chrome else {}),args=['--disable-gpu'])
    page=browser.new_page(viewport={'width':960,'height':240})
    data=json.loads((ROOT/'dist/contributions.json').read_text())
    frames,eaten,duration=plan(data['days'])
    for theme in ('light','dark'):
        svg=(ROOT/f'dist/piggy-{theme}.svg').read_text()
        page.set_content(svg)
        for t in (0,min(eaten.values(),default=.8),duration-.3,duration+.1):
            page.evaluate('(t)=>{let s=document.querySelector("svg");s.pauseAnimations();s.setCurrentTime(t)}',t)
            assert page.locator('svg').evaluate('(s)=>s.getBBox().width')>0
        encoded=base64.b64encode(svg.encode()).decode()
        page.set_content(f'<img src="data:image/svg+xml;base64,{encoded}">')
        page.wait_for_timeout(150)
        assert page.locator('img').evaluate('(i)=>i.complete && i.naturalWidth>0')
        first=page.locator('img').screenshot()
        page.wait_for_timeout(1200)
        assert first!=page.locator('img').screenshot(), 'Embedded image did not animate'
        print(f'PASS {theme}: SVG loads and animates as an image; loop/eating states render')
    browser.close()
