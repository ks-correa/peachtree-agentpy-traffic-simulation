"""Package reviewed chart improvements and verify every pre-change scientific hash."""
import hashlib,json,zipfile
from ui.presentation_data import ROOT,ASSETS,read_json

def main():
    before=read_json('presentation_assets/pre_chart_improvement_hashes.json')
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in before}
    assert before==after,'Scientific artifact changed'
    qa=read_json('presentation_assets/chart_test_report.json');browser=read_json('presentation_assets/chart_browser_qa.json')
    assert qa['failures']==qa['errors']==0 and qa['technical_UI_passed'] and not browser['page_errors']
    audit=read_json('presentation_assets/presentation_chart_audit.json')
    assert audit['all_presentation_ready'] and audit['all_technical_charts_ready']
    audit.update(visual_review='40 PNG inspected via seven contact sheets and full-size representative figures; Chrome UI screenshots reviewed.',
        total_visualizations_audited=audit['audited_figures']+audit['technical_UI_charts_audited'],
        existing_export_figures_updated=32,new_export_figures=8,
        modified_files=[r['filename'] for r in audit['figures']],
        scientific_result_hashes_intact=True,scientific_files_verified=len(before),
        status='ALL PRESENTATION CHARTS UNDERSTANDABLE WITHOUT HOVER',scientific_status='SCIENTIFIC RESULTS UNCHANGED')
    (ASSETS/'presentation_chart_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    (ASSETS/'post_chart_improvement_hashes.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
    manifest=read_json('presentation_assets/presentation_manifest.json');manifest['chart_status']=audit['status']
    manifest['chart_audit']='presentation_chart_audit.json';manifest['generated_PNG_count']=len(list(ASSETS.glob('*.png')))
    for slide in manifest['slides']:
        prefix=f'{slide["slide_number"]:02}_'
        slide['supporting_figure_files']=[r['filename'] for r in audit['figures'] if r['filename'].startswith(prefix) and r['filename']!=slide['figure_file']]
        if slide['slide_number']==8:slide['supporting_figure_files'].append('08_base_simulation_capture.png')
    (ASSETS/'presentation_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    final=read_json('presentation_assets/final_presentation_report.json')
    final.update(chart_improvement_QA=qa,chart_browser_QA=browser,assets_PNG=manifest['generated_PNG_count'],
        scientific_freezes_and_results_intact=True,chart_status=audit['status'])
    (ASSETS/'final_presentation_report.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(ASSETS/'presentation_material.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in ASSETS.rglob('*'):
            if not p.is_file() or p.suffix=='.zip' or p.name.startswith(('pre_','post_','chart_review_')):continue
            if any(part in ['screenshots','chart_browser'] for part in p.relative_to(ASSETS).parts):continue
            z.write(p,p.relative_to(ASSETS))
    print(json.dumps({'audited':audit['total_visualizations_audited'],'PNG_figures':audit['audited_figures'],'tests_passed':qa['passed'],
        'scientific_files_intact':len(before),'ZIP_bytes':(ASSETS/'presentation_material.zip').stat().st_size}))

if __name__=='__main__':main()
