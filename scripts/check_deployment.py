from pathlib import Path
import json,subprocess,datetime,hashlib,requests
R=Path(__file__).resolve().parents[1];base='https://ancoded1234.github.io/movie-poster-color-analysis/'
meta=json.loads(subprocess.check_output(['gh','api','repos/ancoded1234/movie-poster-color-analysis/pages'],text=True))
files={}
for path in ['index.html','assets/app.js','assets/style.css','data/analysis.json']:
    response=requests.get(base+path,timeout=30);response.raise_for_status()
    content=response.content;local=(R/'docs'/path).read_bytes();assert content.replace(b'\r\n',b'\n')==local.replace(b'\r\n',b'\n'),f'Deployed content differs: {path}'
    files[path]={'http_status':response.status_code,'sha256':hashlib.sha256(content).hexdigest()}
record={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':base,'public_unauthenticated_http':True,'github_pages_status':meta['status'],'source':meta['source'],'assets':files}
(R/'results/deployment.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2))
