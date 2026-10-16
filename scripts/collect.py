from pathlib import Path
import os,json,datetime,requests,zipfile
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
for p in [ROOT,*ROOT.parents]:
    if (p/'.env').is_file():
        load_dotenv(p/'.env',override=False)
        print('Loaded existing .env:',p/'.env');break
for d in ['data/raw','data/firecrawl','results','docs/data','docs/assets']:(ROOT/d).mkdir(parents=True,exist_ok=True)
def firecrawl():
    key=os.getenv('FIRECRAWL_API_KEY');print('FIRECRAWL_API_KEY configured:',bool(key))
    sources=[]
    urls=['https://blog.adobe.com/en/publish/2018/02/27/idmovieweek-designing-show-stopping-posters-type','https://arxiv.org/abs/2309.12022','https://www.studiobinder.com/blog/movie-genres-list/','https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00368/full']
    for i,url in enumerate(urls):
        entry={'url':url,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Firecrawl v2 scrape'}
        if key:
            try:
                r=requests.post('https://api.firecrawl.dev/v2/scrape',headers={'Authorization':f'Bearer {key}'},json={'url':url,'formats':['markdown'],'onlyMainContent':True},timeout=100)
                entry['http_status']=r.status_code
                j=r.json();data=j.get('data',{});entry['source_status']=data.get('metadata',{}).get('statusCode');entry['success']=bool(j.get('success')) and entry['source_status']==200
                entry['title']=data.get('metadata',{}).get('title','');entry['characters']=len(data.get('markdown',''))
                (ROOT/f'data/firecrawl/{i}_full.json').write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf-8')
                # Short factual record only; full copyrighted source stays local.
            except Exception as e:entry.update(success=False,error=type(e).__name__)
        else:entry.update(success=False,error='Missing API key')
        sources.append(entry);print('Firecrawl',i,entry.get('http_status'),entry.get('success'))
    (ROOT/'data/firecrawl/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
def kaggle():
    print('Kaggle credential configured:',bool(os.getenv('KAGGLE_API_TOKEN') or (os.getenv('KAGGLE_USERNAME') and os.getenv('KAGGLE_KEY')) or (Path.home()/'.kaggle/kaggle.json').exists()))
    url='https://www.kaggle.com/api/v1/datasets/download/raman77768/movie-classifier'
    dest=ROOT/'data/raw/movie-classifier.zip'
    if not dest.exists():
        with requests.get(url,stream=True,timeout=120) as r:
            print('Kaggle public download HTTP:',r.status_code);r.raise_for_status()
            with dest.open('wb') as f:
                for chunk in r.iter_content(1024*1024):f.write(chunk)
    print('Archive bytes:',dest.stat().st_size)
    with zipfile.ZipFile(dest) as z:
        names=z.namelist();print('Files:',len(names),'sample:',names[:12]);z.extractall(ROOT/'data/raw/dataset')
    print('CSVs:',[str(p.relative_to(ROOT)) for p in (ROOT/'data/raw/dataset').rglob('*.csv')])
if __name__=='__main__':
    import sys
    firecrawl() if '--firecrawl' in sys.argv else kaggle()
