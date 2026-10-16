from pathlib import Path
import json,ast,subprocess
import pandas as pd,numpy as np
from dotenv import dotenv_values
R=Path(__file__).resolve().parents[1];D=json.loads((R/'results/analysis.json').read_text(encoding='utf-8'));F=pd.read_csv(R/'results/color_features.csv');raw=pd.read_csv(R/'data/raw/dataset/Multi_Label_dataset/train.csv');assert len(raw.drop_duplicates())==raw.Id.nunique();raw=raw.drop_duplicates('Id');assert F.Id.is_unique;assert F.sha256.is_unique
assert len(F)==1000;assert F.genre.value_counts().eq(250).all();assert F.groupby(['genre','split']).size().loc[(slice(None),'test')].eq(50).all()
lookup=raw.set_index('Id');assert all(lookup.loc[r.Id,D['genres']].sum()==1 and lookup.loc[r.Id,r.genre]==1 for _,r in F.iterrows())
assert set(F[F.split=='train'].sha256).isdisjoint(F[F.split=='test'].sha256)
for s in D['summary']:
    for k in ['r','g','b','saturation','brightness','dark','luminance']:assert np.isclose(s[k],F.loc[F.genre==s['genre'],k].mean())
    assert np.isclose(sum(p['ratio'] for p in s['palette']),1)
assert sum(map(sum,D['confusion']))==200
assert json.loads((R/'docs/data/analysis.json').read_text(encoding='utf-8'))==D
source=json.loads((R/'data/firecrawl/sources.json').read_text(encoding='utf-8'));assert len(source)==4 and all(s['success'] and s['source_status']==200 for s in source)
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=R,text=True).splitlines();secrets=[]
for parent in [R,*R.parents]:
    if (parent/'.env').exists():secrets=[v for v in dotenv_values(parent/'.env').values() if v and len(v)>15];break
for f in files:
    p=R/f;assert not f.endswith('.env') and not f.startswith('data/raw/') and '_full.json' not in f
    if p.is_file():
        content=p.read_bytes();assert not any(v.encode() in content for v in secrets),'Secret detected in publishable file'
result={'label_links_correct':True,'balanced_sample':True,'train_test_hash_disjoint':True,'aggregations_match_csv':True,'firecrawl_sources_valid':4,'publishable_files_secret_scan':'passed','publishable_files':len(files)}
(R/'results/data_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
