"""Standalone numerical audit figures, no frontend fitting."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calibration.structural import OUT
from calibration.structural_metrics import stopped,STOP_FT_S
from simulation.training_data import load_inputs
from simulation.signals import controllers_from_inputs

def main():
    figures=OUT/'figures';figures.mkdir(exist_ok=True)
    datasets=[('REAL_B2',pd.read_parquet(OUT/'real_observations.parquet')),('OLD_BASELINE',pd.read_parquet(OUT/'old_observations.parquet')),('REVISED_BASELINE',pd.read_parquet(OUT/'revised_observations.parquet'))]
    precision=[];motion=[]
    for label,data in datasets:
        d=data.sort_values(['id','frame']);g=d.groupby('id');dy=(d.y-g.y.shift())*np.where(d.direction==2,1,-1);valid=d.frame.sub(g.frame.shift()).eq(1)
        precision.append({'series':label,'literal_zero_fraction':d.speed.eq(0).mean(),'rounded_to_source_0_01_ft_s_zero_fraction':np.round(d.speed,2).eq(0).mean(),
            'reported_precision_ft_s':.01,'interpretation':'Diagnostic observation operator from reported output precision, not primary stopped classifier or physics'})
        for lo,hi in [(0.,0.),(0.,.1),(.1,.25),(.25,.5),(.5,1.),(1.,2.)]:
            mask=valid&((d.speed==0) if hi==0 else ((d.speed>lo)&(d.speed<=hi)));z=dy[mask]/.1
            motion.append({'series':label,'speed_band_low_ft_s':lo,'speed_band_high_ft_s':hi,'n':len(z),'constant_y_fraction':z.eq(0).mean(),
                'backwards_position_step_fraction':z.lt(0).mean(),'signed_displacement_speed_median_ft_s':z.median(),'absolute_displacement_speed_P95_ft_s':z.abs().quantile(.95)})
    pd.DataFrame(precision).to_csv(OUT/'observation_precision_audit.csv',index=False);pd.DataFrame(motion).to_csv(OUT/'low_speed_displacement_audit.csv',index=False)
    colors=['#16787c','#666fae','#bd6c29']
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained')
    edges=np.arange(0,3.0001,.01)
    for (label,d),color in zip(datasets,colors):
        counts=np.histogram(d.speed,edges)[0]/len(d);axes[0].step(edges[:-1],counts,where='post',label=label,color=color)
        x=np.sort(d.speed[d.speed.between(0,3)]);axes[1].plot(x,np.arange(1,len(x)+1)/len(d),label=label,color=color)
    axes[0].set(xlabel='Speed(ft/s)',ylabel='Fraction of ALL frames /0.01ft/s bin',title='Reported speed near zero (including zero atom)');axes[0].set_ylim(bottom=0)
    axes[1].set(xlabel='Speed(ft/s)',ylabel='Cumulative fraction of ALL frames',title='Operational threshold fixed independently')
    axes[1].axvline(STOP_FT_S,color='black',linestyle='--',label='0.1m/s external operational convention');axes[0].legend();axes[1].legend()
    fig.savefig(figures/'low_speed_semantics.png',dpi=150);plt.close(fig)
    episodes=pd.read_csv(OUT/'stop_episodes_detail.csv');fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for label,color in zip([x[0] for x in datasets],colors):
        x=np.sort(episodes[(episodes.series==label)&~episodes.left_censored&~episodes.right_censored].duration_s);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label,color=color)
    ax.set(xlabel='Complete episode duration(s)',ylabel='ECDF',title='TRAIN: same operational classifier, censoring excluded');ax.legend();ax.grid(alpha=.2);fig.savefig(figures/'stop_episode_comparison.png',dpi=150);plt.close(fig)
    inputs=load_inputs();bank=controllers_from_inputs(inputs);cross=pd.read_csv(OUT/'signal_crossings.csv')
    for (inter,direction),c in bank.items():
        fig,axes=plt.subplots(3,1,figsize=(12,6),sharex=True,layout='constrained');times=np.arange(0,inputs['horizon_s'],.1)
        axes[0].step(times,[{'RED':0,'YELLOW':1,'GREEN':2,'UNKNOWN':-1}[c.at(t)] for t in times],where='post',color='#19727a');axes[0].set_yticks([0,1,2],['RED','YELLOW','GREEN'])
        for (label,d),color in zip(datasets,colors):
            z=d[(d.intersection==inter)&(d.direction==direction)].copy();z['stop']=stopped(z.speed);counts=z.groupby('time').stop.sum();axes[1].plot(counts.index,counts,label=label,color=color,alpha=.8)
            cc=cross[(cross.series==label)&(cross.intersection==inter)&(cross.direction==direction)];edges=np.arange(0,inputs['horizon_s']+10,10);axes[2].step(edges[:-1],np.histogram(cc.time,edges)[0],where='post',label=label,color=color)
        axes[0].set_title(f'TRAIN B2 signal plan - I{inter}, direction{direction}');axes[1].set_ylabel('Operational stopped count');axes[2].set_ylabel('Crossings /10s');axes[2].set_xlabel('Simulation time(s)');axes[1].legend();axes[2].legend()
        fig.savefig(figures/f'signal_{inter}_{direction}.png',dpi=140);plt.close(fig)
    queue=pd.read_csv(OUT/'queue_timeseries.csv');fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
    for ax,(inter,direction) in zip(axes.flat,bank):
        for label,color in zip([x[0] for x in datasets],colors):
            z=queue[(queue.series==label)&(queue.intersection==inter)&(queue.direction==direction)];ax.plot(z.time,z.queue,label=label,color=color,alpha=.85)
        ax.set(title=f'I{inter} direction{direction}',xlabel='Time(s)',ylabel='Connected operational queue');ax.grid(alpha=.2)
    axes.flat[0].legend();fig.savefig(figures/'queue_comparison.png',dpi=140);plt.close(fig)
    # SIGNAL_RELEASE_DELAY and queued green discharge measured on the same sample definition.
    release=pd.read_csv(OUT/'green_release_delay.csv');fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for label,color in zip([x[0] for x in datasets],colors):
        x=np.sort(release[release.series.eq(label)&release.queue_rank.eq(1)&~release.censored].release_delay_s)
        if len(x):ax.plot(x,np.arange(1,len(x)+1)/len(x),label=label,color=color)
    ax.set(xlabel='First target-head observed green release delay(s)',ylabel='ECDF',title='Observable release timing, not cognitive reaction time');ax.legend();fig.savefig(figures/'green_release_comparison.png',dpi=150);plt.close(fig)
    queued=[]
    for label,d in datasets:
        events=cross[cross.series.eq(label)]
        for (inter,direction),controller in bank.items():
            for interval in controller.intervals:
                if interval.state!='GREEN' or interval.start<0:continue
                at=d[np.isclose(d.time,interval.start-.1,atol=1e-6)&d.intersection.eq(inter)&d.direction.eq(direction)&d.lane.isin([1,2])&d.distance.between(0,100)&d.speed.le(STOP_FT_S)]
                for lane,q in at.groupby('lane'):
                    e=events[events.id.isin(q.id)&events.lane.eq(lane)&events.time.between(interval.start,interval.end,inclusive='left')].sort_values('time')
                    for before,after in zip(e.time.to_numpy(),e.time.to_numpy()[1:]):queued.append({'series':label,'intersection':inter,'direction':direction,'lane':lane,'green_start':interval.start,'headway_s':after-before,'population':'TARGET already queued within100ft before green; not fully observed saturation if background omitted'})
    pd.DataFrame(queued).to_csv(OUT/'queued_discharge_headway.csv',index=False)
    # Coverage and descriptive RED/stop correlations; not offset calibration.
    align=pd.read_csv(OUT/'signal_alignment_audit.csv')
    for idx,row in align.iterrows():
        c=bank[(int(row.intersection),int(row.direction))];grid=np.arange(round(inputs['horizon_s']/.1)+1)*.1
        phase=np.array([c.at(t) for t in grid]);align.loc[idx,'unknown_clock_ticks']=np.sum(phase=='UNKNOWN')
        z=datasets[0][1];z=z[(z.intersection==row.intersection)&(z.direction==row.direction)].copy();z['tick']=np.rint(z.time/.1).astype(int);z['stop']=stopped(z.speed)
        counts=z.groupby('tick').stop.sum().reindex(range(len(grid)),fill_value=0).to_numpy();red=phase=='RED'
        align.loc[idx,'RED_indicator_stopped_count_correlation']=np.corrcoef(red.astype(float),counts)[0,1]
    align.to_csv(OUT/'signal_alignment_audit.csv',index=False)
    print('Figures generated; queued discharge:',pd.DataFrame(queued).groupby('series').headway_s.agg(['count','mean','median']).to_string())
if __name__=='__main__':main()
