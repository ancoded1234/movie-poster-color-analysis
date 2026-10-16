from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];D=json.loads((R/'results/analysis.json').read_text(encoding='utf-8'));S=D['summary'];G=D['genres'];plt.style.use('dark_background');colors=['#a5b6b7','#e9ab8d','#b9bba0','#e6ce7f']
out=R/'results/figures';out.mkdir(exist_ok=True)
fig,ax=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for i,key in enumerate(['brightness','saturation']):
    ax[i].bar(G,[s[key] for s in S],color=colors);ax[i].set(ylim=(0,1),title='Mean HSV '+key,ylabel='0–1');ax[i].spines[['top','right']].set_visible(False)
fig.savefig(out/'brightness_saturation.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7,5),layout='constrained');cm=np.array(D['confusion']);ax.imshow(cm,cmap='YlGn');ax.set(xticks=range(4),xticklabels=G,yticks=range(4),yticklabels=G,xlabel='Predicted',ylabel='Actual',title=D['best_model']+' / holdout')
for i in range(4):
    for j in range(4):ax.text(j,i,str(cm[i,j]),ha='center',va='center',color='black' if cm[i,j]<30 else 'white')
fig.savefig(out/'confusion_matrix.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for g,c,s in zip(G,colors,S):
    p=[x for x in D['points'] if x['genre']==g];ax[0].scatter([x['brightness'] for x in p],[x['saturation'] for x in p],s=7,alpha=.4,color=c,label=g);ax[1].plot(['R','G','B'],[s[k] for k in ['r','g','b']],color=c,marker='o',label=g)
ax[0].set(xlim=(0,1),ylim=(0,1),xlabel='Mean HSV V',ylabel='Mean HSV S',title='Poster distributions');ax[1].set(ylim=(0,1),title='Mean RGB');ax[1].legend();fig.savefig(out/'color_distributions.png',dpi=180);plt.close(fig)
# Original poster contact sheet is retained locally in ignored raw data only.
from PIL import Image,ImageDraw
examples=[next(x for x in D['examples'] if x['actual']==g) for g in G];sheet=Image.new('RGB',(720,320),'#101111');draw=ImageDraw.Draw(sheet)
for i,e in enumerate(examples):
    im=Image.open(R/f'data/raw/dataset/Multi_Label_dataset/Images/{e["id"]}.jpg').convert('RGB');im.thumbnail((170,250));sheet.paste(im,(i*180,0));draw.text((i*180,255),e['actual']+' > '+e['predicted'],fill='white');draw.text((i*180,280),e['id'],fill='white')
sheet.save(R/'data/raw/local_poster_examples.jpg')
print('Saved three exportable figures and a local-only poster contact sheet.')
