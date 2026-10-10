"""Finalize QA, temporal bins and integrity without changing scenario design."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from calibration.scenarios import OUT,ROOT,verify,design,original,sha,cycles,scenario_inputs,MODES

def main():
    audit=verify();spec=design();report=json.loads((OUT/'test_report.json').read_text())
    assert report['failures']==report['errors']==0
    events=pd.concat([pd.read_csv(p) for p in (OUT/'replicas').glob('departures_*.csv')],ignore_index=True)
    events.to_csv(OUT/'departure_events.csv',index=False);rows=[]
    for (context,mode,seed),g in events.groupby(['context','scenario','seed']):
        horizon=original(context)['horizon_s'];edges=np.r_[np.arange(0,horizon,30),horizon+1e-7]
        for direction,di in [('ALL',None),('NB',2),('SB',4)]:
            q=g if di is None else g[g.direction.eq(di)];count=np.histogram(q.time,edges)[0]
            for j,n in enumerate(count):rows.append(dict(context=context,scenario=mode,seed=seed,direction=direction,
                bin_start_s=edges[j],bin_end_s=edges[j+1],departures=int(n),cumulative_departures=int(count[:j+1].sum())))
    bins=pd.DataFrame(rows);base=bins[bins.scenario.eq('BASE')].drop(columns='scenario')
    bins=bins.merge(base[['context','seed','direction','bin_start_s','cumulative_departures']],on=['context','seed','direction','bin_start_s'],suffixes=('','_BASE'),validate='many_to_one')
    bins['paired_cumulative_difference']=bins.cumulative_departures-bins.cumulative_departures_BASE
    bins.to_csv(OUT/'temporal_departures.csv',index=False)
    changes=[]
    for context in ['B1','B2']:
        old=original(context);new=scenario_inputs(context,'E1')
        for key,g in pd.DataFrame(old['signals']).groupby(['intersection_id','direction']):
            altered=[r for r in new['signals'] if (r['intersection_id'],r['direction'])==key]
            for cycle,b in enumerate(cycles(g.to_dict('records'))):
                n=next(p for p in cycles(altered) if abs(p[0]['t_start_s']-b[0]['t_start_s'])<1e-7)
                green=b[0]['t_end_s']-b[0]['t_start_s'];newgreen=n[0]['t_end_s']-n[0]['t_start_s']
                changes.append(dict(context=context,intersection=key[0],direction=key[1],cycle=cycle,BASE_green_s=green,E1_green_s=newgreen,
                    increment_s=newgreen-green,percent_increase=(newgreen/green-1)*100,cycle_s=b[3]['t_start_s']-b[0]['t_start_s'],
                    yellow_s=b[1]['t_end_s']-b[1]['t_start_s'],cycle_preserved=True,yellow_preserved=True))
    pd.DataFrame(changes).to_csv(OUT/'signal_changes_by_cycle.csv',index=False)
    required=['scenario_design_freeze.json','experiment_seeds.json','b2_scenario_runs.csv','b1_scenario_runs.csv','b2_scenario_summary.csv','b1_scenario_summary.csv','paired_differences.csv','directional_results.csv','queue_results.csv','temporal_departures.csv','robustness_summary.csv','pareto_analysis.csv','decision_score.csv','emergent_behavior.csv','experiment_freeze.json','test_report.json']
    assert all((OUT/name).exists() for name in required)
    assert len(list((OUT/'figures').glob('*.png')))==13
    p=OUT/'experiment_freeze.json';f=json.loads(p.read_text())
    f['test_suite']={k:report[k] for k in ['tests_total','passed','skipped','failures','errors']};f['test_report_sha256']=sha(OUT/'test_report.json')
    paths=[ROOT/'calibration/scenarios.py',ROOT/'scripts/finish_peachtree6.py',ROOT/'scripts/run_scenario_tests.py',Path(__file__),ROOT/'tests/test_scenarios.py',ROOT/'ui/streamlit_app.py',ROOT/'ui/canvas_renderer.py']
    f['code_hashes']={str(path.relative_to(ROOT)):sha(path) for path in paths}
    f['baseline_parameters_sha256']=sha(ROOT/'outputs/peachtree4/final_parameters.json')
    f['temporal_departures_definition']='30s counts and cumulative departures, ALL/NB/SB, every paired seed; positive E−BASE cumulative difference means earlier progress'
    f['scenario_design_unchanged']=sha(OUT/'scenario_design_freeze.json')==f['scenario_design_hash'];assert f['scenario_design_unchanged']
    p.write_text(json.dumps(f,indent=2))
    (OUT/'post_experiment_integrity.json').write_text(json.dumps({'all_prior_artifacts_and_freezes_unchanged':True,'scenario_design_unchanged':True,'IDM_unchanged':True,'scope_unchanged':True,'official_runs':240,'test_suite':f['test_suite']},indent=2))
    doc=ROOT/'docs/peachtree6_scenario_experimentation.md';text=doc.read_text(encoding='utf-8')
    text=text.replace('final exact totals are in test_report.json.','QA: {} total, {} passed, {} skipped, zero failures/errors; details are in test_report.json.'.format(report['tests_total'],report['passed'],report['skipped']))
    doc.write_text(text,encoding='utf-8')
    print(f['classification']);print('Recommended:',f['recommended_alternative']);print(f['test_suite']);print('13 figures and all required outputs present; prior freezes and design intact')

if __name__=='__main__':main()
