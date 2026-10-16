# Can Color Predict Movie Genres?

영화 포스터의 색상만으로 영화 장르를 예측할 수 있을까? 데이터 리터러시 중간고사 프로젝트 / **CINEMATIC DATA LAB**.

**발표 URL: https://ancoded1234.github.io/movie-poster-color-analysis/**

저장소: https://github.com/ancoded1234/movie-poster-color-analysis

## 실제 데이터 수집과 정제

- 수집일: 2026-10-16 (UTC). Kaggle [Movie Posters](https://www.kaggle.com/datasets/raman77768/movie-classifier), `raman77768/movie-classifier`.
- Kaggle 인증 파일·환경변수는 없었지만 공개 Kaggle API 다운로드가 HTTP 200으로 성공했다. 아카이브 259,590,154 bytes, 이미지 **7,867장**, CSV **7,254행**. 고유 Id는 7,242개이며 동일 라벨의 중복 행은 12개다. Id로 라벨을 연결하지 못하는 추가 이미지 625장은 분석에서 제외했다.
- CSV의 `Id` → `Images/{Id}.jpg`. `Genre` 리스트와 25개 one-hot 장르 컬럼 일치 여부를 전체 CSV에서 검증: 불일치 0건.
- 목표 4장르 해당 개수: 0개 2,480편, 1개 3,494편, 2개 1,254편, 3개 26편. 2개 이상인 1,280편을 한 장르로 임의 배정하지 않았다.
- 목표 장르가 정확히 하나인 영화만 4분류에 사용했다. Drama·Thriller 등 다른 장르는 공존하므로 순수 단일 장르 분류가 아니다.
- 전체 CSV 연결 이미지에 누락 0건, 손상 0건. 목표 장르 1개인 후보에서 RGB 디코딩 SHA-256 중복 7장, 64-bit dHash 해밍 거리 ≤4인 근접 중복 1장을 제거했다. 전체 이미지 데이터셋의 중복 수가 아니라 이 분석 후보의 제외 수다.
- 정제 후보: Horror 331장, Romance 510장, Action 923장, Comedy 1,722장. 고정 seed 42로 장르별 250장씩, 총 **1,000장**을 표본 추출했다. 균형화에 복제·증강을 사용하지 않았다.

## 색채 추출과 모델

1. EXIF 방향 보정, RGB 변환, 동일한 96×144 Lanczos 리사이즈. 종횡비는 정규화되며 alpha 이미지는 RGB로 변환된다.
2. 평균 RGB(0–1), HSV S/V 평균, sRGB 감마 해제 후 상대 휘도(0.2126R+0.7152G+0.0722B), 어두운 픽셀(V<0.2), 고채도(S>0.6), warm/cool/neutral 비율.
3. 유채색은 S≥0.2, warm은 Hue<90° 또는 ≥330°, cool은 나머지. 이 분할은 분석의 조작적 정의이며 보편적 색채 분류가 아니다. 무채색은 warm/cool에서 제외한다.
4. RGB 4×4×4 구간 Shannon entropy(bits)로 다양성, 휘도 표준편차로 명암 대비, √ΣRGB 분산으로 색 대비 계산. RGB 64구간 및 유채색 Hue 12구간 히스토그램 포함, 총 **90개** 입력 변수.
5. 이미지마다 8픽셀 간격 표본으로 K-means 5색(n_init=3, seed=42)을 학습하고 전체 픽셀을 배정해 비율 계산. 장르 팔레트는 포스터별 5색을 비율 가중 K-means로 요약한다. 모든 포스터의 총 가중치는 동일하다. HEX 색은 반올림된 중심이다.
6. 층화 80:20 훈련/테스트 분리: **800/200장**. 중복은 분리 전에 제거. 훈련에서만 5-fold StratifiedGroupKFold, 그룹=이미지 해시. Logistic Regression의 스케일링은 Pipeline 안에서 fold별 학습.
7. Dummy(most_frequent), Logistic Regression(C=1, max_iter=3000), Random Forest(300 trees, min_samples_leaf=4, max_features=sqrt). 별도 하이퍼파라미터 탐색 없이 훈련 CV Macro F1 최고 모델 **Random Forest** 선택. 테스트 점수로 선택하거나 튜닝하지 않았다.

영화 제목, 줄거리, OCR, 의미 임베딩, 공간 특징은 입력하지 않았다. 포스터 속 문자 자체의 픽셀 색은 포함된다.

## 결과

|장르|표본 수|평균 명도 V|평균 채도 S|어두운 픽셀|최대 군집색|
|---|---:|---:|---:|---:|---|
|Horror|250|33.4%|39.2%|47.8%|#0f0c0d|
|Romance|250|54.6%|35.4%|21.9%|#1b1515|
|Action|250|41.7%|40.4%|35.7%|#141111|
|Comedy|250|64.0%|34.0%|14.0%|#e9e9e6|

|모델|테스트 Accuracy|Macro Precision|Macro Recall|Macro F1|훈련 5-fold Macro F1 ± SD|
|---|---:|---:|---:|---:|---:|
|Dummy|25.0%|0.062|0.250|0.100|0.100 ± 0.000|
|Logistic Regression|43.5%|0.428|0.435|0.430|0.462 ± 0.039|
|Random Forest|47.5%|0.469|0.475|0.469|0.493 ± 0.046|

색상은 기준선 이상의 정보를 제공했지만 높은 신뢰도의 단독 장르 분류기는 아니다. 공포는 상대적으로 어둡고, 코미디는 밝았다. 공포→액션뿐 아니라 액션→공포 오분류가 많아 어두운 팔레트가 여러 장르에서 겹침을 확인했다. 평균 차이는 관찰 결과이며 인과관계나 유의성 검정의 결과가 아니다.

### 해석의 한계

편의 표본으로 시대·국가·배급사를 통제하지 않았다. 목표 장르 중복작 제외는 쉬운 표본 쪽 선택 편향을 만들 수 있다. 원본 장르 라벨의 정확성은 사람이 전수 확인하지 않았다. dHash는 유사 포스터를 놓치거나 서로 다른 이미지를 제외할 수 있고, 속편·시리즈에 따른 스타일 누수까지 완전히 차단하지 못한다. 1,000장 균형 표본의 성능은 실제 장르 빈도·다중 라벨 환경 성능과 다르다. 테스트는 장르당 50장이며 단일 분할이다. 평균 색상 차이가 사용자 반응이나 디자인 효과를 입증하지 않는다.

## Firecrawl와 출처

기존 상위 `.env`를 python-dotenv로 `override=False`로 읽었다. 새 `.env`를 만들지 않았으며 키 값은 출력·저장하지 않는다. Firecrawl v2 scrape로 공개 자료 4건을 수집하고 **API 응답과 원본 metadata.statusCode=200을 함께 검증**했다. 초기에 요청한 Adobe/StudioBinder 자료 2개는 404여서 정상 자료로 교체했다.

- [Adobe: Designing Show-Stopping Posters With Type](https://blog.adobe.com/en/publish/2018/02/27/idmovieweek-designing-show-stopping-posters-type): 이미지와 타이포그래피를 통한 스토리 표현의 배경.
- [Demystifying Visual Features of Movie Posters for Multi-Label Genre Identification](https://arxiv.org/abs/2309.12022): 포스터 기반 다중 라벨 연구. 이 프로젝트의 색상 전용 모델과 직접 성능 비교하지 않는다.
- [StudioBinder: Movie Genres](https://www.studiobinder.com/blog/movie-genres-list/): 장르 개념과 사례의 배경.
- [Elliot 2015: Color and psychological functioning](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00368/full): 색채 심리 연구와 응용에서 맥락·신중함이 필요하다는 문헌. 장르별 특정 색의 정답을 입증하는 자료로 사용하지 않는다.

`data/firecrawl/sources.json`에 URL·수집시각·HTTP 상태·자료 제목을 보관한다. 전문은 로컬 `*_full.json`으로 저장하고 공개 Git에서는 제외했다. 웹 문헌은 배경 자료이며 이미지의 주 수집원은 Kaggle이다.

## 실행 환경 / 재현

Windows PowerShell, Python 3.12.15. 버전은 `requirements.txt`에 고정했다. 프로젝트와 동일한 위치 또는 상위 경로에 이미 존재하는 `.env`에서 FIRECRAWL_API_KEY를 읽는다. `.env`를 커밋하지 말 것.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe scripts/collect.py
.venv/Scripts/python.exe scripts/collect.py --firecrawl
.venv/Scripts/python.exe scripts/analyze.py
.venv/Scripts/python.exe scripts/figures.py
.venv/Scripts/python.exe scripts/document.py
.venv/Scripts/python.exe -m http.server 8765 --directory docs
```

다른 터미널에서 브라우저 검증:

```powershell
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe scripts/qa.py http://localhost:8765
```

방향키·PageUp/PageDown·Home/End·화면 버튼으로 이동, F 또는 발표 모드 버튼으로 전체 화면. 데스크톱 16:9 프레젠테이션 프레임, 작은 화면은 내용에 맞춘 반응형 세로 확장. 팔레트에 마우스/키보드 초점을 두면 색상·비율을 확인할 수 있다. 차트는 실측 JSON을 직접 읽으며 외부 차트 CDN에 의존하지 않는다. Google Fonts 실패 시 시스템 sans-serif로 표시된다. CSS print 모드도 제공한다.

## 주요 파일

```text
data/raw/                    # 원본 압축/이미지, 로컬 포스터 사례 (Git 제외)
data/firecrawl/              # 출처 기록, 전문은 Git 제외
scripts/collect.py           # 기존 .env 로딩, Kaggle API / Firecrawl 수집
scripts/analyze.py           # 검증, 특징 추출, EDA 집계, 모델 평가
scripts/figures.py           # PNG 그래프와 로컬 원본 포스터 사례
scripts/document.py          # 실측 결과 기반 README
scripts/qa.py                # 4개 화면 크기 × 12장 브라우저 검증
results/color_features.csv   # 실제 1,000장 색채 특성과 split
results/all_eligible_features.csv # 정제된 전체 후보 특성
results/image_audit.csv      # 행별 검증 / 제외 이유
results/label_patterns.csv   # 전체 목표 장르 다중 라벨 패턴
results/model_metrics.csv    # 세 모델 성능
results/test_predictions.csv # 테스트 포스터별 예측
results/analysis.json        # 집계/혼동행렬/사례/산점도
results/figures/             # 내보내기용 PNG 그래프
docs/index.html             # 12장 인터랙티브 발표자료
docs/assets/                # CSS / JS
docs/data/analysis.json      # 발표자료가 읽는 실제 데이터
```

## 공개 범위와 배포

원본 포스터의 재배포 허가가 명확하지 않아 공개 화면에는 팔레트와 색상 통계만 게시했다. 실제 포스터 사례 contact sheet는 로컬 `data/raw/local_poster_examples.jpg`에만 보관한다. 원본 대용량 이미지, API 키, 인증 파일, `.env`, 웹 문헌 전문은 업로드하지 않는다.

GitHub CLI로 새 공개 저장소를 만들고 main 브랜치를 push했다. GitHub Pages는 공식 REST API로 source=main, path=/docs를 지정한다. URL: **https://ancoded1234.github.io/movie-poster-color-analysis/**. 검증 내역은 `results/browser_qa.json` 및 `results/deployment.json`에서 확인한다.
