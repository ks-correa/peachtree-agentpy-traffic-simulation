"""UI/export regression checks; never execute scientific experiments."""
import json,unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from ui.presentation_data import ROOT,ASSETS,read_json

def main():
    suite=unittest.TestSuite()
    for name in ['test_presentation_dashboard.py','test_presentation_chart_labels.py']:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=name))
    with (ASSETS/'chart_test_details.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    import agentpy
    with patch.object(agentpy.Model,'run',side_effect=AssertionError('Scientific execution prohibited')):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60);app.session_state['dashboard_mode']='TECHNICAL MODE';app.run()
        assert not app.exception
    technical=[]
    for i,node in enumerate(app.get('plotly_chart'),1):
        fig=json.loads(node.proto.spec);layout=fig['layout'];annotations=layout.get('annotations',[])
        item=dict(ui_identifier=f'TECHNICAL_{i:02}',title=layout['title']['text'],
            axes_clear=all(layout.get(axis,{}).get('title',{}).get('text') not in ['value','time','simulation_time','probability','variable'] for axis in ['xaxis','yaxis']),
            static_values_visible=any(any(word in a.get('text','') for word in ['final','mediana','máximo']) for a in annotations),
            source_visible=any(a.get('text','').startswith('Fuente:') for a in annotations),
            source_artifact=layout.get('meta',{}).get('source_artifact'))
        item['presentation_ready']=item['axes_clear'] and item['static_values_visible'] and item['source_visible'];technical.append(item)
    audit=read_json('presentation_assets/presentation_chart_audit.json');audit['technical_UI_charts']=technical
    audit['technical_UI_charts_audited']=len(technical);audit['all_technical_charts_ready']=all(r['presentation_ready'] for r in technical)
    (ASSETS/'presentation_chart_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'tests':result.testsRun,'passed':result.testsRun-len(result.errors)-len(result.failures),'failures':len(result.failures),'errors':len(result.errors),
        'technical_UI_charts_checked':len(technical),'technical_UI_passed':audit['all_technical_charts_ready'],'no_scientific_experiments':True}
    (ASSETS/'chart_test_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    if not result.wasSuccessful() or not audit['all_technical_charts_ready']:raise SystemExit(1)

if __name__=='__main__':main()
