"""Pure JS unit test with mocked DOM/Canvas, not browser automation."""
import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from ui.canvas_renderer import render_canvas

class CanvasPlaybackTests(unittest.TestCase):
    def test_script_executes_and_playback_updates_only_frontend(self):
        metric=dict(vehicles_active=1,vehicles_entered=0,initial_vehicles=1,vehicles_exited=0,mean_speed_ft_s=10.,throughput_cumulative=0,travel_time_mean_s=None,stopped_vehicles=0,queue_proxy_vehicles=0)
        agent=dict(agent_id='SIM-1',position=500.,direction=2,lane=1,speed=10.,length_ft=15.,**{'class':2})
        trace={'network':{'stop_lines':[]},'frames':[{'time':0.,'agents':[agent],'metrics':metric,'signals':{}},{'time':10.,'agents':[dict(agent,position=600.)],'metrics':metric,'signals':{}}]}
        html=render_canvas(trace,'unit',True,8.,True);script=html.split('<script>')[1].split('</script>')[0]
        harness=r'''
const vm=require('node:vm'),assert=require('node:assert');let callback,storage={};
const ctx=new Proxy({}, {get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>{o[k]=v;return true}});
const canvas={clientWidth:1000,width:0,height:0,getContext:()=>ctx};
const elements=new Map();const element=k=>{if(!elements.has(k))elements.set(k,{style:{},textContent:'',innerHTML:''});return elements.get(k)};
const root={isConnected:true,querySelector:k=>k==='#corridor'?canvas:element(k)};
const environment={window:{devicePixelRatio:1},document:{getElementById:()=>root},sessionStorage:{getItem:k=>storage[k],setItem:(k,v)=>storage[k]=v},performance:{now:()=>0},requestAnimationFrame:f=>{callback=f;return 1},cancelAnimationFrame:()=>{},Map,Number,Math,console};
vm.runInNewContext(SOURCE,environment);callback(100);
assert.equal(element('#metric-0').textContent,'0.8 s');assert.equal(element('#metric-1').textContent,'1');assert.equal(storage['ngsim-clock-unit'],'0.8');
environment.window.ngsimStop();assert.equal(storage['ngsim-clock-unit'],'0.8');console.log('Canvas RAF/render/persistence: PASS');
'''.replace('SOURCE',json.dumps(script))
        node=shutil.which('node');self.assertIsNotNone(node)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'canvas_unit.js';path.write_text(harness,encoding='utf-8')
            result=subprocess.run([node,str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('PASS',result.stdout)
        self.assertEqual(trace['frames'][0]['agents'][0]['position'],500.)
