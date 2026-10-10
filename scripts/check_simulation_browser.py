"""Check all eight saved scenarios, playback controls and direct downloads in Chrome."""
import io,json
from PIL import Image
from playwright.sync_api import sync_playwright
from ui.presentation_data import ASSETS,read_json
from ui.simulation_view import SCENARIOS

def select(page,label,text):
    page.get_by_label(label,exact=True).click();page.get_by_role('option',name=text,exact=True).click();page.wait_for_timeout(1100)

def current_frame(page,context,scenario):
    for frame in page.frames:
        if frame.locator('#ngsim-live').count():
            frame.wait_for_function('window.ngsimPresentationAudit != null')
            if frame.evaluate('window.ngsimPresentationAudit.context')==context and frame.evaluate('window.ngsimPresentationAudit.scenario')==scenario:return frame
    raise AssertionError('Selected trace iframe missing')

def verify(frame,trace,total):
    state=frame.evaluate('window.ngsimPresentationAudit')
    sample=max((f for f in trace['frames'] if f['time']<=state['clock']),key=lambda f:f['time'])
    assert state['signals']==sample['signals']
    assert state['metrics']==sample['metrics']
    entered=sample['metrics']['vehicles_entered']+sample['metrics']['initial_vehicles']
    assert frame.locator('#demand-0').inner_text()==str(total)
    assert frame.locator('#demand-1').inner_text()==str(entered)
    assert frame.locator('#demand-4').inner_text()==str(total-entered)
    assert frame.locator('#metric-1').inner_text()==str(sample['metrics']['vehicles_active'])+' veh'
    return state

def main():
    folder=ASSETS/'simulation_browser';folder.mkdir(exist_ok=True);exports=ASSETS/'simulation_exports';exports.mkdir(exist_ok=True)
    results=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1080})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8510',wait_until='networkidle');page.get_by_role('tab',name='Simulación',exact=True).click();page.wait_for_timeout(1200)
        select(page,'Ventana visual','60 s');select(page,'Playback','x10')
        for context in ['B1','B2']:
            select(page,'Contexto de simulación',context+' — '+('Validación' if context=='B1' else 'Calibración'))
            for scenario,name in SCENARIOS.items():
                select(page,'Escenario de simulación',scenario+' — '+name)
                assert page.locator('[data-testid="stException"]').count()==0
                trace=read_json(f'outputs/peachtree6/traces/{context}_{scenario}_7000.json')
                inputs=read_json('outputs/peachtree5/b1_exogenous_inputs.json' if context=='B1' else 'outputs/peachtree3u/final_inputs.json')
                total=len(inputs['initial'])+len(inputs['entries']);frame=current_frame(page,context,scenario)
                initial=verify(frame,trace,total);assert abs(initial['horizon_s']-inputs['horizon_s'])<1e-7
                assert frame.locator('#ngsim-live').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(255, 255, 255)'
                assert page.locator('.modebar:visible').count()==0
                assert page.locator('[data-testid="stPlotlyChart"]:visible').count()==8
                titles=page.locator('.js-plotly-plot').evaluate_all('(es)=>es.map(e=>e.layout.title.text)')
                assert all(context in title for title in titles[:7]),titles
                page.get_by_role('button',name='Iniciar',exact=True).click();page.wait_for_timeout(1100)
                page.get_by_role('button',name='Pausar',exact=True).click();page.wait_for_timeout(600)
                frame=current_frame(page,context,scenario);paused=verify(frame,trace,total);assert paused['clock']>0
                frame.locator('#ngsim-live').screenshot(path=str(folder/f'{context}_{scenario}.png'))
                page.get_by_role('button',name='Continuar',exact=True).click();page.wait_for_timeout(6500)
                frame=current_frame(page,context,scenario);final=verify(frame,trace,total);assert abs(final['clock']-60)<.05
                assert frame.locator('#demonstration-status').inner_text()=='Demostración finalizada'
                results.append(dict(context=context,scenario=scenario,horizon_s=initial['horizon_s'],scheduled_target=total,
                    correct_saved_signals=True,correct_live_metrics=True,official_context_verified=True,
                    run_pause_continue=True,demonstration_end=True,white_canvas=True,charts=8))
                page.get_by_role('button',name='Reiniciar',exact=True).click();page.wait_for_timeout(600)
                assert current_frame(page,context,scenario).evaluate('window.ngsimPresentationAudit.clock')==0
        select(page,'Ventana visual','Completa');frame=current_frame(page,'B2','E3')
        full=frame.evaluate('window.ngsimPresentationAudit');assert full['end_s']==full['horizon_s']
        # Exercise every graph's deferred PNG and its matching CSV from this same section.
        for i in range(8):
            with page.expect_download(timeout=60000) as download:page.get_by_role('button',name='Descargar PNG',exact=True).nth(i).click()
            path=exports/download.value.suggested_filename;download.value.save_as(str(path))
            with Image.open(path) as image:assert image.size==(1920,1080) and image.info['source_artifact']
            with page.expect_download() as csv:page.get_by_role('button',name='Descargar CSV',exact=True).nth(i).click()
            csvpath=exports/csv.value.suggested_filename;csv.value.save_as(str(csvpath));assert 'source_artifact' in csvpath.read_text(encoding='utf-8-sig').splitlines()[0]
        select(page,'Modo','TECHNICAL MODE');page.wait_for_timeout(1000)
        assert page.locator('[data-testid="stException"]').count()==0
        assert page.locator('[data-testid="stPlotlyChart"]:visible').count()==8
        page.get_by_text('Detalles técnicos de la corrida',exact=True).click()
        page.screenshot(path=str(folder/'technical_mode.png'))
        browser.close()
    report={'combinations':results,'checked':len(results),'PNG_downloads':8,'CSV_downloads':8,'technical_same_layout':True,
        'full_visual_window_matches_official_horizon':True,'page_errors':errors,'new_scientific_experiments':False}
    (ASSETS/'simulation_browser_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    assert not errors;print('8/8 combinations, playback, matching states/signals, 8 PNG + 8 CSV downloads and technical layout passed.')

if __name__=='__main__':main()
