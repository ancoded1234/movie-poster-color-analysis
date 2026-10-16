"""Extend saved audit with source ID accounting without retraining models."""
from pathlib import Path
import json,pandas as pd
R=Path(__file__).resolve().parents[1];raw=R/'data/raw/dataset/Multi_Label_dataset';df=pd.read_csv(raw/'train.csv')
assert len(df.drop_duplicates())==df.Id.nunique()
extra=dict(unique_ids=int(df.Id.nunique()),duplicate_id_rows=int(df.Id.duplicated().sum()),unlabeled_images=len({p.stem for p in (raw/'Images').glob('*.jpg')}-set(df.Id)))
D=json.loads((R/'results/analysis.json').read_text(encoding='utf-8'));D['audit'].update(extra)
for path in ['results/analysis.json','docs/data/analysis.json']:(R/path).write_text(json.dumps(D,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'results/audit.json').write_text(json.dumps(D['audit'],ensure_ascii=False,indent=2),encoding='utf-8')
p=R/'scripts/document.py';s=p.read_text(encoding='utf-8').replace("{A['image_files']-A['rows']}","{A['unlabeled_images']}").replace('Id로 라벨을 연결하지 못하는','고유 Id는 7,242개이며 동일 라벨의 중복 행은 12개다. Id로 라벨을 연결하지 못하는');p.write_text(s,encoding='utf-8')
print(extra)
p=R/'docs/assets/app.js';s=p.read_text(encoding='utf-8').replace('CSV 라벨 행','CSV 원본 행 · 중복 12행')
if '위 집계는 원본 행 기준.' not in s:
    s=s.replace('목표 4장르 중 정확히 하나에 속한 영화만 사용.','위 집계는 원본 행 기준. 고유 영화 7,242편, 라벨 없는 이미지 625장 제외. 목표 4장르 중 정확히 하나에 속한 영화만 사용.')
p.write_text(s,encoding='utf-8')
