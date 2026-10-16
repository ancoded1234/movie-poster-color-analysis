from pathlib import Path
import json,hashlib,ast,datetime
import numpy as np,pandas as pd,cv2
from PIL import Image,ImageOps
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split,StratifiedGroupKFold,cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,confusion_matrix,classification_report
from threadpoolctl import threadpool_limits
threadpool_limits(2)
R=Path(__file__).resolve().parents[1]; G=['Horror','Romance','Action','Comedy'];seed=42
def save(path,obj):
    (R/path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def features(path):
    with Image.open(path) as im:
        im=ImageOps.exif_transpose(im).convert('RGB').resize((96,144),Image.Resampling.LANCZOS)
        a=np.asarray(im);rgb=a.reshape(-1,3).astype(float)/255
        hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV).reshape(-1,3).astype(float);h=hsv[:,0]*2;s=hsv[:,1]/255;v=hsv[:,2]/255
        lin=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);lum=lin@np.array([.2126,.7152,.0722])
        chrom=s>=.2;warm=chrom&((h<90)|(h>=330));cool=chrom&(h>=90)&(h<330)
        hist=np.histogramdd(rgb,bins=(4,4,4),range=((0,1),)*3)[0].ravel();hist/=hist.sum();nz=hist[hist>0]
        f=dict(zip(['r','g','b'],rgb.mean(axis=0)));f.update(saturation=s.mean(),brightness=v.mean(),luminance=lum.mean(),dark=(v<.2).mean(),high_saturation=(s>.6).mean(),warm=warm.mean(),cool=cool.mean(),neutral=(~chrom).mean(),diversity=-(nz*np.log2(nz)).sum(),color_contrast=np.sqrt(rgb.var(axis=0).sum()),light_contrast=lum.std())
        for i,n in enumerate(hist):f[f'rgb_bin_{i}']=n
        for i,n in enumerate(np.histogram(h[chrom],bins=12,range=(0,360))[0]/len(h)):f[f'hue_bin_{i}']=n
        km=KMeans(5,random_state=seed,n_init=3).fit(rgb[::8]);counts=np.bincount(km.predict(rgb),minlength=5)/len(rgb);order=np.argsort(-counts)
        pal=[{'hex':'#'+''.join(f'{int(c):02x}' for c in np.clip(np.rint(km.cluster_centers_[i]*255),0,255)),'ratio':float(counts[i])} for i in order]
        # dHash groups visually near-identical resized posters as well as exact decoded images.
        gray=np.asarray(im.convert('L').resize((9,8)));dh=np.packbits(gray[:,1:]>gray[:,:-1]).tobytes().hex()
        return f,pal,hashlib.sha256(a.tobytes()).hexdigest(),int(dh,16)
def main():
    base=R/'data/raw/dataset/Multi_Label_dataset';df=pd.read_csv(base/'train.csv');assert df.Id.notna().all()
    assert len(df.drop_duplicates())==df.Id.nunique(),'Conflicting labels for duplicate ID'
    mismatches=sum(set(ast.literal_eval(row.Genre))!={g for g in df.columns[2:] if row[g]==1} for _,row in df.iterrows())
    assert mismatches==0,'Text/one-hot label mismatch'
    df['target_count']=df[G].sum(axis=1);audit={'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':len(df),'image_files':len(list((base/'Images').glob('*'))),'label_columns':list(df.columns[2:-1]),'label_mismatches':mismatches,'target_overlap':df.target_count.value_counts().sort_index().to_dict(),'full_genre_counts':{g:int(df[g].sum()) for g in df.columns[2:-1]},'missing':0,'corrupt':0,'exact_duplicates':0,'near_duplicates':0}
    audit.update(unique_ids=int(df.Id.nunique()),duplicate_id_rows=int(df.Id.duplicated().sum()),unlabeled_images=len({p.stem for p in (base/'Images').glob('*.jpg')}-set(df.Id)))
    df['target_pattern']=df[G].apply(lambda r:' + '.join(g for g in G if r[g]),axis=1);df.target_pattern.value_counts().to_csv(R/'results/label_patterns.csv')
    rows=[];seen={};hashes=[];manifest=[]
    for i,row in df.iterrows():
        path=base/'Images'/f'{row.Id}.jpg';record={'Id':row.Id,'Genre':row.Genre,'target_count':int(row.target_count),'status':'valid'}
        if not path.exists():audit['missing']+=1;record['status']='missing';manifest.append(record);continue
        try:
            with Image.open(path) as im: im.verify()
        except Exception:audit['corrupt']+=1;record['status']='corrupt';manifest.append(record);continue
        if row.target_count!=1:record['status']='excluded_target_overlap_or_zero';manifest.append(record);continue
        f,pal,sha,dh=features(path)
        if sha in seen:audit['exact_duplicates']+=1;record['status']='exact_duplicate';manifest.append(record);continue
        if any((dh-h0==0) or ((dh^h0).bit_count()<=4) for h0 in hashes):audit['near_duplicates']+=1;record['status']='near_duplicate';manifest.append(record);continue
        seen[sha]=row.Id;hashes.append(dh);genre=next(g for g in G if row[g]==1)
        rows.append(dict(Id=row.Id,genre=genre,genres=row.Genre,sha256=sha,**f,palette=pal));manifest.append(record)
        if len(rows)%200==0:print('Features:',len(rows),flush=True)
    pd.DataFrame(manifest).to_csv(R/'results/image_audit.csv',index=False)
    full=pd.DataFrame(rows);audit['eligible_clean_counts']=full.genre.value_counts().to_dict();n=min(250,int(full.genre.value_counts().min()));assert n>=100
    selected=pd.concat([full[full.genre==g].sample(n,random_state=seed) for g in G]).reset_index(drop=True)
    # Whole-image dHash groups were removed before sampling; no duplicate image crosses splits.
    X=selected.drop(columns=['Id','genre','genres','sha256','palette']);y=selected.genre
    tr,te=train_test_split(np.arange(len(y)),test_size=.2,stratify=y,random_state=seed)
    selected['split']='train';selected.loc[te,'split']='test';selected.to_csv(R/'results/color_features.csv',index=False);full.to_csv(R/'results/all_eligible_features.csv',index=False)
    models={'Dummy':DummyClassifier(strategy='most_frequent'),'Logistic Regression':make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,C=1)),'Random Forest':RandomForestClassifier(n_estimators=300,min_samples_leaf=4,max_features='sqrt',random_state=seed,n_jobs=2)}
    cv=StratifiedGroupKFold(5,shuffle=True,random_state=seed);metrics=[];fitted={}
    for name,m in models.items():
        scores=cross_validate(m,X.iloc[tr],y.iloc[tr],groups=selected.sha256.iloc[tr],cv=cv,scoring=['accuracy','f1_macro'],n_jobs=1)
        m.fit(X.iloc[tr],y.iloc[tr]);p=m.predict(X.iloc[te]);pr,re,f1,_=precision_recall_fscore_support(y.iloc[te],p,average='macro',zero_division=0)
        metrics.append(dict(model=name,accuracy=accuracy_score(y.iloc[te],p),precision=pr,recall=re,macro_f1=f1,cv_accuracy=float(scores['test_accuracy'].mean()),cv_f1=float(scores['test_f1_macro'].mean()),cv_f1_std=float(scores['test_f1_macro'].std())))
        fitted[name]=m;print(metrics[-1],flush=True)
    best=max(metrics,key=lambda a:a['cv_f1'])['model'];pred=fitted[best].predict(X.iloc[te]);prob=fitted[best].predict_proba(X.iloc[te])
    examples=[]
    for j,idx in enumerate(te):examples.append(dict(id=selected.iloc[idx].Id,actual=y.iloc[idx],predicted=pred[j],correct=bool(pred[j]==y.iloc[idx]),confidence=float(prob[j].max()),palette=selected.iloc[idx].palette))
    pd.DataFrame([{k:v for k,v in e.items() if k!='palette'} for e in examples]).to_csv(R/'results/test_predictions.csv',index=False)
    cm=confusion_matrix(y.iloc[te],pred,labels=G).tolist();summary=[]
    for g in G:
        sub=selected[selected.genre==g];colors=np.array([list(bytes.fromhex(p['hex'][1:])) for pal in sub.palette for p in pal]);weights=np.array([p['ratio'] for pal in sub.palette for p in pal]);km=KMeans(5,random_state=seed,n_init=10).fit(colors,sample_weight=weights);tot=np.bincount(km.labels_,weights=weights,minlength=5);order=np.argsort(-tot)
        palette=[{'hex':'#'+''.join(f'{int(c):02x}' for c in np.clip(np.rint(km.cluster_centers_[i]),0,255)),'ratio':float(tot[i]/tot.sum())} for i in order]
        summary.append(dict(genre=g,n=len(sub),palette=palette,**{c:float(sub[c].mean()) for c in X.columns},brightness_sd=float(sub.brightness.std()),saturation_sd=float(sub.saturation.std())))
    audit.update(sample_per_genre=n,analyzed=len(selected),train=len(tr),test=len(te),feature_count=len(X.columns))
    report=dict(audit=audit,genres=G,summary=summary,models=metrics,best_model=best,confusion=cm,classification_report=classification_report(y.iloc[te],pred,output_dict=True,zero_division=0),examples=sorted(examples,key=lambda e:-e['confidence']),points=[dict(genre=r.genre,brightness=r.brightness,saturation=r.saturation,r=r.r,g=r.g,b=r.b) for _,r in selected.iterrows()])
    save('results/analysis.json',report);save('docs/data/analysis.json',report);save('results/audit.json',audit)
    pd.DataFrame(metrics).to_csv(R/'results/model_metrics.csv',index=False);pd.DataFrame(summary).drop(columns='palette').to_csv(R/'results/genre_summary.csv',index=False)
    print(json.dumps(audit,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
