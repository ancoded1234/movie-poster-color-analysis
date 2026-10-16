from pathlib import Path
import json,sys
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];out=R/'test-results';out.mkdir(exist_ok=True);url=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765';report=[]
with sync_playwright() as p:
    b=p.chromium.launch();page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    for w,h in [(1440,900),(1280,720),(768,1024),(390,844)]:
        page.set_viewport_size({'width':w,'height':h});page.goto(url);page.wait_for_selector('.slide.active');page.evaluate('document.fonts.ready');
        for i in range(12):
            page.evaluate('(n)=>{location.hash=String(n)}',i+1);page.wait_for_timeout(500)
            assert page.locator('.slide.active').count()==1
            assert page.locator('#page').inner_text()==f'{i+1:02d} / 12'
            assert page.locator('.slide.active .kicker').first.bounding_box()['y']>=page.locator('header').bounding_box()['height'],('content overlaps header',w,i+1)
            dims=page.evaluate('''()=>{let s=document.querySelector('.slide.active'),r=s.getBoundingClientRect();let elems=[...s.querySelectorAll('h1,h2,h3,p,table,svg,.palette,.matrix,.spark')];return {width:innerWidth,docWidth:document.documentElement.scrollWidth,bottom:Math.max(...elems.map(x=>x.getBoundingClientRect().bottom)),footer:document.querySelector('footer').getBoundingClientRect().top}}''')
            assert dims['docWidth']<=w+2,('horizontal overflow',w,i+1,dims)
            assert dims['bottom']<=dims['footer']+2,('content overlaps footer',w,i+1,dims)
            report.append(dict(height=h,slide=i+1,**dims))
            if w==1440 and i in [0,5,6,8,9]:page.screenshot(path=str(out/f'slide-{i+1:02d}.png'),full_page=True)
            if w==390 and i==8:page.screenshot(path=str(out/'mobile-models.png'),full_page=True)
        page.keyboard.press('Home');assert page.locator('#page').inner_text()=='01 / 12';page.keyboard.press('ArrowRight');assert page.locator('#page').inner_text()=='02 / 12';page.locator('#next').click();assert page.locator('#page').inner_text()=='03 / 12';page.locator('#prev').click();assert page.locator('#page').inner_text()=='02 / 12'
    page.set_viewport_size({'width':1440,'height':900});page.locator('#fullscreen').click();page.wait_for_timeout(100);assert page.evaluate('!!document.fullscreenElement');page.evaluate('document.exitFullscreen()')
    assert not errors,errors;b.close()
(R/'results/browser_qa.json').write_text(json.dumps({'url':url,'checks':len(report),'javascript_errors':errors,'layouts':report},indent=2),encoding='utf-8');print('PASS: 48 slide/viewport combinations, keyboard, buttons, fullscreen, no JS errors.')
