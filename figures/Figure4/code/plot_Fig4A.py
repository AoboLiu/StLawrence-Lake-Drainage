from pathlib import Path
import sys, os
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import pandas as pd,numpy as np,matplotlib.pyplot as plt
from common_panel_utils import despine
f4a=pd.read_csv(ROOT/'Figure4/data/Figure4A_eventweek_medians_for_consistent_plotting.csv')
f4sum=pd.read_csv(ROOT/'Figure4/data/Figure4A_summary.csv')
relabel={'temperature (30 d)':'Temperature (30 d)','precipitation (week 1)':'Precipitation (week 1)','snowmelt (week 2)':'Snowmelt (week 2)','snowmelt (week 1)':'Snowmelt (week 1)','runoff (week 1)':'Runoff (week 1)'}
f4a['label']=f4a.label.replace(relabel);f4sum['label']=f4sum.label.replace(relabel)
sum_lookup=f4sum.set_index('label').to_dict('index');order4=['Temperature (30 d)','Precipitation (week 1)','Snowmelt (week 2)','Snowmelt (week 1)','Runoff (week 1)'];short_map={'Temperature (30 d)':'temp','Precipitation (week 1)':'precip','Snowmelt (week 2)':'snow','Snowmelt (week 1)':'snow','Runoff (week 1)':'runoff'};colmap={'temp':'#E15759','precip':'#59A14F','snow':'#8E63B6','runoff':'#4C78A8'}
xlims={'Temperature (30 d)':(-4.2,1.9),'Precipitation (week 1)':(-11.5,27.5),'Snowmelt (week 2)':(-26,112),'Snowmelt (week 1)':(-26,112),'Runoff (week 1)':(-12.5,50)}
fig,axs=plt.subplots(5,1,figsize=(6.35,8.85),facecolor='white')
for idx,(ax,label) in enumerate(zip(axs,order4),start=1):
 sub=f4a[f4a.label==label];x=sub.delta.values;color=colmap[short_map[label]];vp=ax.violinplot([x],positions=[1],vert=False,widths=.56,showextrema=False)
 for pc in vp['bodies']:
  verts=pc.get_paths()[0].vertices;verts[verts[:,1]<1.0,1]=1.0;pc.set_facecolor(color);pc.set_edgecolor(color);pc.set_alpha(.18)
 ys=np.random.default_rng(idx).uniform(.80,1.20,size=len(x));ax.scatter(x,ys,s=14,color=color,alpha=.7,edgecolors=color,linewidths=.2,zorder=3)
 s=sum_lookup[label];ax.plot([s['CI_low'],s['CI_high']],[.87,.87],color=color,lw=2,solid_capstyle='round');ax.scatter([s['median_delta']],[.87],s=38,color=color,edgecolors='white',linewidths=.45,zorder=4);ax.axvline(0,color='.6',lw=.85,ls='--')
 ax.text(.985,.90,f"median Δ = {s['median_delta']:+.2f} {s['unit']}\n95% CI {s['CI_low']:+.2f} to {s['CI_high']:+.2f}",transform=ax.transAxes,ha='right',va='center',fontsize=7.8,color='#333')
 ax.set_ylim(.72,1.33);ax.set_yticks([]);ax.set_xlim(*xlims[label]);
 if label in ['Snowmelt (week 2)','Snowmelt (week 1)']:ax.set_xticks([-20,0,20,40,60,80,100])
 ax.set_ylabel(label,rotation=90,labelpad=11,va='center',fontsize=8.6);ax.set_xlabel(f"Matched event-week Δ ({s['unit']})",fontsize=10);despine(ax)
fig.subplots_adjust(left=.26,right=.99,bottom=.05,top=.94,hspace=.99);fig.savefig(ROOT/'Figure4/panels/Fig4A.png',facecolor='white',bbox_inches='tight',pad_inches=.10);plt.close(fig)
