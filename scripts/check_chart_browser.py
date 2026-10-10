"""Read-only browser QA of final figures in both Streamlit modes."""
import json
from playwright.sync_api import sync_playwright
from ui.presentation_data import ASSETS,SECTIONS

def main():
    folder=ASSETS/'chart_browser';folder.mkdir(exist_ok=True);errors=[];sections=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1080},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8510',wait_until='networkidle')
        for i,name in enumerate(SECTIONS):
            page.get_by_role('tab',name=name,exact=True).click();page.wait_for_timeout(1500)
            assert page.locator('[data-testid="stException"]').count()==0,name
            charts=page.locator('[data-testid="stPlotlyChart"]:visible')
            if charts.count() and name in ['Datos','Calibración','Validación','Resultados','Comportamiento emergente','Decisión']:
                for attempt in range(3):
                    try:
                        charts.first.screenshot(path=str(folder/f'{i:02}_chart.png'));break
                    except Exception:
                        if attempt==2:raise
                        page.wait_for_timeout(1000)
            assert page.locator('.modebar:visible').count()==0,'Unexpected toolbar'
            sections.append({'section':name,'plotly_charts':charts.count(),'no_exception':True,'no_toolbar':True})
        page.get_by_label('Modo',exact=True).click();page.get_by_text('TECHNICAL MODE',exact=True).click();page.wait_for_timeout(1600)
        assert page.locator('[data-testid="stException"]').count()==0
        assert page.locator('[data-testid="stPlotlyChart"]').first.locator('path.js-line').count()>0,'Technical curve did not draw'
        page.locator('[data-testid="stPlotlyChart"]').first.screenshot(path=str(folder/'technical_chart.png'))
        browser.close()
    report={'sections':sections,'technical_mode_rendered':True,'page_errors':errors,'scientific_controls_used':False}
    (ASSETS/'chart_browser_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    assert not errors
    print('12 presentation sections + technical chart browser checked; no toolbar, no exceptions.')

if __name__=='__main__':main()
