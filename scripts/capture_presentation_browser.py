"""Fresh headless Chrome QA of presentation UI, never scientific execution."""
import json
from playwright.sync_api import sync_playwright
from ui.presentation_data import ASSETS,SECTIONS

def main():
    folder=ASSETS/'screenshots';folder.mkdir(exist_ok=True);errors=[];results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1050},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8510',wait_until='networkidle')
        page.get_by_role('tab',name='Proyecto',exact=True).wait_for()
        for j,name in enumerate(SECTIONS):
            page.get_by_role('tab',name=name,exact=True).click();page.wait_for_timeout(1100)
            exception=page.locator('[data-testid="stException"]').count()
            if exception:raise RuntimeError('UI exception in '+name)
            page.screenshot(path=str(folder/f'{j+1:02}_{name.replace(" ","_")}.png'))
            results.append({'section':name,'browser_rendered':True,'exceptions':exception})
        page.get_by_role('tab',name='Simulación',exact=True).click();page.wait_for_timeout(700)
        page.get_by_label('Playback',exact=True).click();page.get_by_text('x10',exact=True).click()
        page.get_by_role('button',name='Run',exact=True).click();page.wait_for_timeout(2500)
        page.get_by_role('button',name='Pause',exact=True).click();page.wait_for_timeout(500)
        canvasframe=next(frame for frame in page.frames if frame.locator('#corridor').count())
        assert canvasframe.locator('#metric-0').inner_text().strip()!='—'
        assert canvasframe.locator('#live-cards').inner_text().strip()
        page.screenshot(path=str(folder/'simulation_BASE.png'))
        canvasframe.locator('#ngsim-live').screenshot(path=str(ASSETS/'08_base_simulation_capture.png'))
        page.get_by_role('tab',name='Material para presentación',exact=True).click();page.wait_for_timeout(500)
        with page.expect_download() as download:page.get_by_role('button',name='Download todo el material ·ZIP',exact=True).click()
        download.value.save_as(str(folder/'download_verified.zip'))
        browser.close()
    report={'browser':'Chrome headless','sections':results,'page_errors':errors,'canvas_visible':True,'playback_run_pause_checked':True,'ZIP_download_verified':True}
    (ASSETS/'browser_qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if errors:raise RuntimeError('Browser JS errors: '+str(errors))
    print('12 sections, Canvas playback and ZIP download browser-checked')

if __name__=='__main__':main()
