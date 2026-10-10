"""Finalize UI exports and integrity evidence; no scientific writes or executions."""
import hashlib,json,zipfile
from PIL import Image,PngImagePlugin
from ui.presentation_data import ROOT,ASSETS,read_json
from ui.simulation_view import clock_label

def main():
    before=read_json('presentation_assets/pre_simulation_layout_hashes.json')
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in before}
    assert before==after,'Scientific files changed'
    tests=read_json('presentation_assets/simulation_test_report.json');browser=read_json('presentation_assets/simulation_browser_qa.json')
    assert tests['failures']==tests['errors']==0 and browser['checked']==8 and not browser['page_errors']
    (ASSETS/'post_simulation_layout_hashes.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
    # Update the existing presentation capture with the reviewed light Canvas;
    # save PNG metadata only, preserving captured pixels and physical states.
    capture=ASSETS/'simulation_browser/B2_BASE.png'
    with Image.open(capture) as image:
        meta=PngImagePlugin.PngInfo();meta.add_text('source_artifact','outputs/peachtree6/traces/B2_BASE_7000.json;outputs/peachtree3u/final_inputs.json;UI-only Chrome capture')
        image.save(ASSETS/'08_base_simulation_capture.png',pnginfo=meta)
    pngs=list((ASSETS/'simulation_exports').glob('*.png'));exports=[]
    for p in pngs:
        with Image.open(p) as image:
            assert image.size==(1920,1080)
            exports.append(dict(figure_file=p.relative_to(ASSETS).as_posix(),table_file=p.with_suffix('.csv').relative_to(ASSETS).as_posix(),source_artifact=image.info['source_artifact']))
    contexts={}
    for context,source in [('B1','outputs/peachtree5/b1_exogenous_inputs.json'),('B2','outputs/peachtree3u/final_inputs.json')]:
        inputs=read_json(source);contexts[context]=dict(horizon_s=round(inputs['horizon_s'],1),clock=clock_label(inputs['horizon_s']),
            target=len(inputs['initial'])+len(inputs['entries']),initial=len(inputs['initial']),arrivals=len(inputs['entries']),source_artifact=source)
    report=dict(status='SIMULATION SECTION PRESENTATION READY',separation='CURRENT RUN AND OFFICIAL RESULTS CLEARLY SEPARATED',
        science='SCIENTIFIC RESULTS UNCHANGED',scientific_files_verified=len(before),scientific_hashes_intact=True,
        B1=contexts['B1'],B2=contexts['B2'],
        layout=['Configuración','Contexto y escenario','Progreso temporal y demanda','Canvas claro','Métricas en vivo','Dinámica de la corrida','Resultados oficiales — 30 réplicas','Comportamiento emergente','Interpretación'],
        graphs_per_context=8,technical_same_structure=True,UI_tests=tests,browser_QA=browser,exports=exports,
        playback_source='Frozen AgentPy seed7000 snapshots; no new physics or experiments',
        snapshot_end_note='Snapshots end 0.3 s before the official horizon; the last saved state is held visually without adding physical steps.')
    (ASSETS/'simulation_layout_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=read_json('presentation_assets/presentation_manifest.json')
    manifest['simulation_section']=dict(report='simulation_layout_report.json',status=report['status'],exports=exports)
    slide=manifest['slides'][7];slide['supporting_figure_files']=list(dict.fromkeys(slide.get('supporting_figure_files',[])+[e['figure_file'] for e in exports]))
    (ASSETS/'presentation_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    final=read_json('presentation_assets/final_presentation_report.json');final['simulation_layout_QA']=report
    (ASSETS/'final_presentation_report.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(ASSETS/'presentation_material.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in ASSETS.rglob('*'):
            if not p.is_file() or p.suffix=='.zip' or p.name.startswith(('pre_','post_','chart_review_')):continue
            if any(part in ['screenshots','chart_browser','simulation_browser'] for part in p.relative_to(ASSETS).parts):continue
            archive.write(p,p.relative_to(ASSETS))
    print(json.dumps({'scientific_files_unchanged':len(before),'UI_tests_passed':tests['passed'],'browser_combinations':browser['checked'],'new_export_pairs':len(exports)}))

if __name__=='__main__':main()
