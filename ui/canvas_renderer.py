"""Render simulated AgentPy states only. Playback never changes physical dt."""
import json,math

def finite_json(value):
    if isinstance(value,dict):return {k:finite_json(v) for k,v in value.items()}
    if isinstance(value,list):return [finite_json(v) for v in value]
    if isinstance(value,float) and not math.isfinite(value):return None
    return value

def render_canvas(trace,run_id,playing=False,speed=8.,reset=False,show_envelopes=False,show_heads=False,show_effective=False,show_progression=False,presentation=False,light=False,view=None):
    payload=json.dumps(finite_json(trace),separators=(',',':')).replace('</','<\\/')
    config=json.dumps({'id':run_id,'playing':playing,'speed':speed,'reset':reset,'show_envelopes':show_envelopes,'show_heads':show_heads,'show_effective':show_effective,'show_progression':show_progression,'presentation':presentation,'view':view})
    template=TEMPLATE
    if light:
        palette={'#dbe4f0':'#102a43','#101b2b':'#ffffff','#26364b':'#d9e2ef',
            '#142237':'#f4f7fb','#25364e':'#d9e2ef','#91a4bb':'#52667a',
            '#1c2a3b':'#cbd5e1','#26364a':'#e2e8f0','#d0daea':'#102a43',
            '#42536b':'#94a3b8','#7f94ac':'#52667a','#94a3b8':'#64748b',
            '#71869f':'#52667a','#5eead4':'#007f73','#a5b4fc':'#7352a3',
            '#fbbf24':'#b67a12','#fb7185':'#c64764','#38bdf8':'#027da3',
            '#253348':'#e2e8f0','#2dd4bf':'#007f73'}
        for old,new in palette.items():template=template.replace(old,new)
    result=template.replace('__DATA__',payload).replace('__CONFIG__',config)
    return result.replace('Stop lines: proxies observados','EFFECTIVE_SIGNAL_CONTROL_REFERENCE' if trace.get('mode') in ['FINAL_STRUCTURE','FINAL_CALIBRATED_B2','SCENARIO_EXPERIMENTATION'] else 'LEGACY_SIGNAL_PROXY')

TEMPLATE=r'''
<style>
 #ngsim-live *{box-sizing:border-box} #demand-cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:14px 0}
 #live-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
 .view-card{background:#f4f7fb;border:1px solid #d9e2ef;padding:12px;border-radius:10px;font-size:12px;color:#52667a}.view-card strong{display:block;font-size:22px;color:#102a43;margin-top:5px}
 @media(max-width:650px){#demand-cards{grid-template-columns:repeat(3,minmax(0,1fr))}#live-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.canvas-overlay{font-size:10px!important;max-width:170px}}
</style>
<div id="ngsim-live" style="font-family:Inter,Segoe UI,sans-serif;color:#dbe4f0;background:#101b2b;border:1px solid #26364b;border-radius:16px;padding:20px">
 <div id="view-progress" style="display:none;margin-bottom:24px">
  <div style="font-size:13px;font-weight:600">TIEMPO SIMULADO</div><div id="simulation-time" style="font-size:32px;font-weight:700;margin:8px 0"></div>
  <div id="horizon-percent" style="font-size:14px;margin-bottom:10px"></div>
  <div style="height:10px;background:#e2e8f0;border-radius:8px;overflow:hidden"><div id="horizon-progress" style="height:10px;background:#007f73;width:0%"></div></div>
  <div id="demonstration-status" style="font-size:13px;margin:10px 0"></div>
  <div id="technical-tick" style="font-size:12px;color:#64748b"></div>
  <h3 style="margin:20px 0 6px">Vehículos TARGET · estado de la demanda</h3>
  <div id="demand-cards"></div><div id="entered-summary" style="font-size:14px"></div>
  <div style="height:6px;background:#e2e8f0;border-radius:6px;margin-top:10px;overflow:hidden"><div id="demand-progress" style="height:6px;background:#7352a3;width:0%"></div></div>
 </div>
 <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px"><span style="font-weight:600">Corredor arterial · Vista esquemática</span><span id="play-status" style="color:#5eead4;font-size:12px"></span></div>
 <div style="position:relative">
 <canvas id="corridor" style="width:100%;height:300px;display:block" aria-label="Simulación de tráfico AgentPy, calles 11th y 12th"></canvas>
 <div id="canvas-overlay" class="canvas-overlay" style="display:none;position:absolute;right:0;top:0;background:rgba(255,255,255,.95);border:1px solid #d9e2ef;border-radius:8px;padding:8px;font-size:12px;color:#102a43"></div>
 </div>
 <div style="display:flex;gap:22px;font-size:12px;color:#94a3b8;margin:8px 0 20px"><span>● <span style="color:#5eead4">Automóvil NB</span></span><span>● <span style="color:#a5b4fc">Automóvil SB</span></span><span>● <span style="color:#fbbf24">Pesado</span></span><span>Stop lines: proxies observados</span></div>
 <h3 id="metrics-heading" style="display:none">Métricas en vivo · corrida ilustrativa</h3><div id="live-cards"></div>
 <div id="legacy-progress" style="height:3px;background:#253348;margin-top:20px;border-radius:4px"><div id="progress" style="height:3px;background:#2dd4bf;width:0%"></div></div>
</div>
<script>
(()=>{
 const data=__DATA__,config=__CONFIG__,frames=data.frames;
 if(window.ngsimStop)window.ngsimStop();
 const root=document.getElementById('ngsim-live'),canvas=root.querySelector('#corridor'),ctx=canvas.getContext('2d');
 const key='ngsim-clock-'+config.id;let saved=0;try{saved=Number(sessionStorage.getItem(key)||0)}catch(e){}
 let clock=config.reset?0:saved,last=performance.now(),index=0,alive=true,handle;
 const lastTime=config.view?config.view.end_s:frames[frames.length-1].time;
 clock=Math.min(clock,lastTime);
 window.ngsimStop=()=>{alive=false;cancelAnimationFrame(handle);try{sessionStorage.setItem(key,String(clock))}catch(e){}};
 const labels=['Tiempo simulado','Activos · Target / Background','Entradas / iniciales','Salidas','Velocidad media','Throughput acumulado','Travel time acumulado','Detenidos / cola'];
 if(config.presentation&&!config.view){labels[0]='Tiempo simulado / Tick';labels.push('Operational stopped %');}
 if(config.view){
  labels.splice(0,labels.length,'Tiempo simulado','Vehículos activos','Vehículos detenidos','Velocidad media','Fracción detenida','Cola actual','Salidas acumuladas','Tiempo de recorrido acumulado');
  root.querySelector('#view-progress').style.display='block';root.querySelector('#metrics-heading').style.display='block';root.querySelector('#canvas-overlay').style.display='block';root.querySelector('#legacy-progress').style.display='none';
  const legend=root.querySelector('div[style*="gap:22px"]');if(legend)legend.lastElementChild.style.display=config.show_effective?'':'none';
  root.querySelector('#demand-cards').innerHTML=['Programados','Ingresaron (incluye iniciales)','Activos','Salieron','Pendientes de entrar'].map((label,i)=>`<div class="view-card">${label}<strong id="demand-${i}">—</strong></div>`).join('');
 }
 root.querySelector('#live-cards').innerHTML=labels.map((label,i)=>`<div style="background:#142237;border:1px solid #25364e;padding:13px;border-radius:10px"><div style="color:#91a4bb;font-size:11px">${label}</div><div id="metric-${i}" style="font-size:22px;font-weight:600;margin-top:5px">—</div></div>`).join('');
 const fmt=(value,digits=0)=>value==null?'—':Number(value).toFixed(digits);
 const timeLabel=value=>{const n=Math.round(value*10),m=Math.floor(n/600),s=(n%600)/10;return String(m).padStart(2,'0')+':'+s.toFixed(1).padStart(4,'0')};
 function draw(now){
  if(!alive || !root.isConnected)return;
  if(config.playing)clock=Math.min(lastTime,clock+Math.min(.25,(now-last)/1000)*config.speed);last=now;
  while(index<frames.length-1&&frames[index+1].time<=clock)index++;
  while(index>0&&frames[index].time>clock)index--;
  let a=frames[index],b=frames[Math.min(index+1,frames.length-1)],alpha=Math.max(0,Math.min(1,(clock-a.time)/Math.max(.001,b.time-a.time)));
  const W=canvas.clientWidth,H=300,dpr=window.devicePixelRatio||1;
  if(canvas.width!==Math.round(W*dpr)){canvas.width=Math.round(W*dpr);canvas.height=H*dpr;}
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
  const left=52,right=W-52,roadTop=94,laneW=30;const X=y=>left+(y-400)/1000*(right-left);
  ctx.fillStyle='#1c2a3b';ctx.fillRect(left,roadTop,right-left,laneW*4);
  for(const [id,low,high] of [[2,630.810,777.753],[3,1155.863,1246.452]]){
   ctx.fillStyle='#26364a';ctx.fillRect(X(low),49,X(high)-X(low),198);
   ctx.fillStyle='#d0daea';ctx.font='600 13px Segoe UI';ctx.textAlign='center';ctx.fillText(id===2?'11th Street':'12th Street',X((low+high)/2),35);
  }
  ctx.strokeStyle='#42536b';ctx.lineWidth=1;ctx.setLineDash([7,9]);
  for(const y of [roadTop+laneW,roadTop+laneW*3]){ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();}
  ctx.setLineDash([]);ctx.strokeStyle='#c7a968';ctx.beginPath();ctx.moveTo(left,roadTop+laneW*2);ctx.lineTo(right,roadTop+laneW*2);ctx.stroke();
  ctx.fillStyle='#7f94ac';ctx.font='12px Segoe UI';ctx.textAlign='left';ctx.fillText('← SB',left,77);ctx.textAlign='right';ctx.fillText('NB →',right,238);
  for(const stop of data.network.stop_lines){
   let x=X(stop.local_y_ft),y=stop.direction===2?roadTop+laneW*2:roadTop;
   const effective=stop.reference_type==='EFFECTIVE_SIGNAL_CONTROL_REFERENCE';
   if(!effective || config.show_effective){
    ctx.strokeStyle=effective?'#38bdf8':'#a9b9cb';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,y+3);ctx.lineTo(x,y+laneW*2-3);ctx.stroke();
    if(effective){ctx.fillStyle='#38bdf8';ctx.font='9px Segoe UI';ctx.textAlign='center';ctx.fillText('EFFECTIVE CONTROL '+stop.local_y_ft+' ft',x,y+(stop.direction===2?laneW*2+29:-27));}
   }
   let state=a.signals[stop.intersection+'-'+stop.direction];ctx.fillStyle=state==='GREEN'?'#34d399':state==='YELLOW'?'#fbbf24':state==='RED'?'#fb7185':'#64748b';
   ctx.beginPath();ctx.arc(x,stop.direction===2?roadTop+laneW*4+13:roadTop-13,4,0,Math.PI*2);ctx.fill();
  }
  const next=new Map(b.agents.map(x=>[x.agent_id,x]));
  if(config.show_progression && data.progression){
   const p=data.progression,up=data.network.stop_lines.find(s=>s.intersection===p.upstream_intersection&&s.direction===p.direction),down=data.network.stop_lines.find(s=>s.intersection===p.downstream_intersection&&s.direction===p.direction);
   if(up&&down){const x1=X(up.local_y_ft),x2=X(down.local_y_ft),y=50;
    ctx.strokeStyle='#38bdf8';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x1,y);ctx.lineTo(x2,y);ctx.stroke();
    ctx.fillStyle='#38bdf8';ctx.font='10px Segoe UI';ctx.textAlign='center';ctx.fillText('Expected progression '+p.DOMINANT_PROGRESSION_DIRECTION+' · '+fmt(p.PROGRESSION_TRAVEL_TIME,2)+' s',(x1+x2)/2,y-9);
    const greens=(data.signal_intervals||[]).filter(s=>s.intersection_id===p.upstream_intersection&&s.direction===p.direction&&s.state==='GREEN').map(s=>s.t_start_s-data.source_window_start_relative_s).filter(t=>t<=clock);
    if(greens.length){const elapsed=clock-Math.max(...greens),ratio=elapsed/p.PROGRESSION_TRAVEL_TIME;if(ratio>=0&&ratio<=1){ctx.beginPath();ctx.arc(x1+(x2-x1)*ratio,y,4,0,Math.PI*2);ctx.fill();}}
   }
  }
  if(data.receiving_scope && (!config.view || config.show_effective)){
   ctx.strokeStyle='#94a3b8';ctx.lineWidth=1;ctx.setLineDash([4,4]);
   for(const direction of [2,4]){const cut=data.receiving_scope.exit_ft[String(direction)],y=direction===2?roadTop+2*laneW:roadTop;
    ctx.beginPath();ctx.moveTo(X(cut),y);ctx.lineTo(X(cut),y+2*laneW);ctx.stroke();
    ctx.fillStyle='#94a3b8';ctx.font='10px Segoe UI';ctx.fillText((direction===2?'NB':'SB')+' EXIT '+cut+' ft',X(cut),direction===2?264:65);
   }ctx.setLineDash([]);
  }
  if(config.show_envelopes)for(const e of (data.control_envelopes||[])){
   const l=e.lane, y=e.direction===2?roadTop+laneW*(l+1):roadTop+laneW*(2-l);
   ctx.fillStyle='rgba(56,189,248,0.12)';ctx.fillRect(X(Math.min(e.approach_start,e.exit)),y,Math.abs(X(e.exit)-X(e.approach_start)),laneW);
   if(e.stop_low!=null && e.stop_high!=null){ctx.fillStyle='rgba(251,191,36,0.25)';ctx.fillRect(X(e.stop_low),y,X(e.stop_high)-X(e.stop_low),laneW);}
   ctx.strokeStyle='#38bdf8';ctx.lineWidth=1;
   for(const ref of [e.entry,e.exit]){ctx.beginPath();ctx.moveTo(X(ref),y);ctx.lineTo(X(ref),y+laneW);ctx.stroke();}
  }
  for(const v of a.agents){
   const n=next.get(v.agent_id),pos=n?v.position+(n.position-v.position)*alpha:v.position;
   const l=v.lane===2?2:1;const y=v.direction===2?roadTop+laneW*(l+1)+laneW/2:roadTop+laneW*(2-l)+laneW/2;
   const length=Math.max(5,v.length_ft/1000*(right-left)),x=X(pos),start=v.direction===2?x-length:x;
   ctx.fillStyle=v.class===3?'#fbbf24':v.direction===2?'#5eead4':'#a5b4fc';ctx.fillRect(start,y-7,length,14);
   ctx.fillStyle='#20364b';ctx.fillRect(v.direction===2?start+length-4:start+1,y-5,3,10);
   if(config.view){
    const front=v.direction===2?start+length:start,rear=v.direction===2?start:start+length;
    ctx.fillStyle='#dbeafe';ctx.fillRect(v.direction===2?front-Math.min(5,length*.35):front+1,y-4,Math.min(4,length*.25),8);
    ctx.fillStyle='rgba(255,255,255,.5)';ctx.fillRect(v.direction===2?rear+1:rear-Math.min(4,length*.25)-1,y-4,Math.min(3,length*.20),8);
    ctx.strokeStyle='#334155';ctx.lineWidth=.8;ctx.strokeRect(start,y-7,length,14);
    if(v.speed<=config.view.stopped_threshold_ft_s){ctx.fillStyle='#dc2626';ctx.fillRect(v.direction===2?rear:rear-2,y-6,2,3);ctx.fillRect(v.direction===2?rear:rear-2,y+3,2,3);}
    if(config.view.technical && config.show_effective){ctx.fillStyle='#102a43';ctx.font='9px Segoe UI';ctx.textAlign='center';ctx.fillText(String(v.agent_id),start+length/2,y-11);}
   }
   if(config.show_heads)for(const head of (a.queue_heads||[]))if(head.id===v.agent_id){
    ctx.strokeStyle='#fb7185';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,y,11,0,Math.PI*2);ctx.stroke();
    ctx.fillStyle='#fb7185';ctx.font='10px Segoe UI';ctx.fillText('Q '+head.queue+' / '+fmt(head.spatial_ft,0)+' ft',x,y-16);
   }
  }
  ctx.fillStyle='#71869f';ctx.font='11px Segoe UI';ctx.textAlign='left';ctx.fillText(config.view&&!config.show_effective?'Entrada NB · Salida SB':'SOUTH CUT · 400 ft',left,280);ctx.textAlign='right';ctx.fillText(config.view&&!config.show_effective?'Salida NB · Entrada SB':'NORTH CUT · 1400 ft',right,280);
  const m=a.metrics,roles=m.target_active==null?'':(' · '+fmt(m.target_active)+' / '+fmt(m.background_active)),values=[fmt(clock,1)+' s',fmt(m.vehicles_active)+roles,fmt(m.vehicles_entered)+' / '+fmt(m.initial_vehicles),fmt(m.vehicles_exited),fmt(m.mean_speed_ft_s,1)+' ft/s',fmt(m.throughput_cumulative)+' veh',fmt(m.travel_time_mean_s,1)+' s',fmt(m.stopped_vehicles)+' / '+fmt(m.queue_proxy_vehicles)];
  if(config.presentation&&!config.view){values[0]=fmt(clock,1)+' s / '+Math.round(clock/.1);values.push(m.vehicles_active?fmt(m.stopped_fraction*100,2)+' %':'—');if(!m.vehicles_active)values[4]='—';}
  if(config.view){
   window.ngsimPresentationAudit={context:data.context,scenario:data.scenario,seed:data.seed,run_id:config.id,horizon_s:config.view.horizon_s,end_s:config.view.end_s,clock:clock,snapshot_time:a.time,signals:a.signals,metrics:m,scheduled_target:config.view.scheduled_target};
   const view=config.view,entered=m.vehicles_entered+m.initial_vehicles,pending=Math.max(0,view.scheduled_target-entered),percent=clock/view.horizon_s*100;
   values.splice(0,values.length,timeLabel(clock),fmt(m.vehicles_active)+' veh',fmt(m.stopped_vehicles)+' veh',m.vehicles_active?fmt(m.mean_speed_ft_s,2)+' ft/s':'—',m.vehicles_active?fmt(m.stopped_fraction*100,2)+' %':'—',fmt(m.queue_proxy_vehicles)+' veh',fmt(m.throughput_cumulative)+' veh',fmt(m.travel_time_mean_s,2)+' s');
   root.querySelector('#simulation-time').textContent=timeLabel(clock)+' / '+timeLabel(view.horizon_s);
   root.querySelector('#horizon-percent').textContent=fmt(percent,1)+'% del horizonte oficial';root.querySelector('#horizon-progress').style.width=percent+'%';
   root.querySelector('#demonstration-status').textContent=clock>=lastTime?(view.partial?'Demostración finalizada':'Horizonte visual finalizado'):'Ventana de demostración: '+timeLabel(view.end_s);
   root.querySelector('#technical-tick').textContent=view.technical?'Tick visual: '+Math.round(clock/.1)+' · último snapshot físico: '+fmt(a.time,1)+' s':'';
   [view.scheduled_target,entered,m.vehicles_active,m.vehicles_exited,pending].forEach((v,i)=>root.querySelector('#demand-'+i).textContent=v);
   root.querySelector('#entered-summary').textContent=entered+' / '+view.scheduled_target+' ingresaron';root.querySelector('#demand-progress').style.width=(entered/view.scheduled_target*100)+'%';
   root.querySelector('#canvas-overlay').innerHTML='<b>'+view.context+' · '+(view.context==='B1'?'VALIDACIÓN':'CALIBRACIÓN')+'</b><br>'+view.scenario+' · '+view.scenario_label+'<br>Tiempo '+timeLabel(clock)+' / '+timeLabel(view.horizon_s)+'<br>Activos '+m.vehicles_active+' · Detenidos '+m.stopped_vehicles;
  }
  values.forEach((value,i)=>root.querySelector('#metric-'+i).textContent=value);
  root.querySelector('#play-status').textContent=clock>=lastTime?'FINALIZADO':config.playing?'REPRODUCIENDO · '+config.speed+'×':'PAUSADO';
  root.querySelector('#progress').style.width=(clock/lastTime*100)+'%';
  try{sessionStorage.setItem(key,String(clock))}catch(e){}
  handle=requestAnimationFrame(draw);
 }
 handle=requestAnimationFrame(draw);
})();
</script>'''
