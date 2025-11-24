# 청년 정책 추천 MVP 실행 가이드 🚀

SQLite + SQLAlchemy ORM 기반 간단한 MVP 버전입니다.

---

## 📋 목차

1. [시스템 구조](#시스템-구조)
2. [설치 및 설정](#설치-및-설정)
3. [실행 방법](#실행-방법)
4. [API 사용법](#api-사용법)
5. [PyCharm 실행](#pycharm-실행)

---

## 🏗️ 시스템 구조

```
MVP 아키텍처:
┌─────────────────────────────────────────────────────────┐
│                   프론트엔드 (React)                      │
│                 http://localhost:5173                    │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST API
┌───────────────────────▼─────────────────────────────────┐
│              FastAPI 서버 (Python)                        │
│                http://localhost:8000                     │
│  - /policies: 정책 목록                                  │
│  - /search: 검색                                         │
│  - /statistics: 통계                                     │
└───────────────────────┬─────────────────────────────────┘
                        │ SQLAlchemy ORM
┌───────────────────────▼─────────────────────────────────┐
│            SQLite 데이터베이스                            │
│              data/youth_policy.db                        │
│  - policies: 정책 데이터                                 │
│  - search_history: 검색 기록                             │
│  - statistics: 통계                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ 설치 및 설정

### 1단계: Python 패키지 설치

```bash
# 가상환경 생성 (선택사항)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2단계: 환경 변수 설정

`.env` 파일 생성 (프로젝트 루트):

```bash
# OpenAI API (선택 - LLM 기능 사용 시)
OPENAI_API_KEY=sk-your-api-key-here

# 데이터베이스 경로 (선택)
DATABASE_DIR=./data

# 로그 레벨
LOG_LEVEL=info
```

---

## ▶️ 실행 방법

### 1단계: 데이터베이스 초기화 및 크롤링

```bash
# 크롤링 실행 및 SQLite에 저장
python scripts/crawl_and_save.py
```

**출력 예시:**
```
============================================================
청년 정책 크롤러 → SQLite 저장
============================================================

[1/3] 데이터베이스 초기화...
📦 데이터베이스 테이블 생성 중...
✅ 데이터베이스 초기화 완료: /path/to/data/youth_policy.db

[2/3] 크롤링 시작...
============================================================
[복지로] 크롤링 시작...
============================================================
✅ 크롤링 완료:
   - 총 정책: 25개
   - 성공: 25개
   - 실패: 0개

💾 데이터베이스에 저장 중...
✅ 저장 완료:
   - 생성: 25개
   - 업데이트: 0개

...

✨ 완료!
```

### 2단계: API 서버 실행

```bash
# FastAPI 서버 시작
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**출력 예시:**
```
============================================================
청년 정책 추천 API 서버 시작
============================================================

📊 데이터베이스 정보:
   경로: /path/to/data/youth_policy.db
   크기: 1.5 MB
   테이블 수: 4

   테이블별 레코드 수:
      - policies: 50개
      - search_history: 0개
      - search_results: 0개
      - statistics: 0개

✅ 서버 준비 완료
   Swagger UI: http://localhost:8000/docs
   ReDoc: http://localhost:8000/redoc
============================================================

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 3단계: 브라우저에서 확인

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 📡 API 사용법

### 1. 헬스 체크

```bash
curl http://localhost:8000/health
```

**응답:**
```json
{
  "status": "healthy",
  "database": "connected",
  "total_policies": 50,
  "active_policies": 50
}
```

### 2. 정책 목록 조회

```bash
curl "http://localhost:8000/policies?limit=5"
```

**응답:**
```json
[
  {
    "id": 1,
    "policy_id": "bokjiro_001",
    "policy_name": "청년 월세 지원",
    "category": "주거",
    "summary": "청년의 주거비 부담 완화를 위한 월세 지원",
    "target_age_min": 19,
    "target_age_max": 34,
    ...
  },
  ...
]
```

### 3. 정책 검색

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "주거 지원",
    "age": 25,
    "income": 30000000,
    "limit": 10
  }'
```

**응답:**
```json
{
  "query": "주거 지원",
  "total_results": 8,
  "response_time": 0.045,
  "results": [...]
}
```

### 4. 카테고리 목록

```bash
curl http://localhost:8000/categories
```

**응답:**
```json
{
  "categories": ["주거", "취업", "교육", "생활지원", "창업"],
  "category_counts": {
    "주거": 15,
    "취업": 12,
    "교육": 10,
    ...
  }
}
```

### 5. 통계 조회

```bash
curl http://localhost:8000/statistics
```

**응답:**
```json
{
  "policies": {
    "total_policies": 50,
    "active_policies": 50,
    "categories": {...}
  },
  "searches": {
    "total_searches": 100,
    "avg_response_time": 0.035,
    "period_days": 7
  },
  "popular_queries": [
    {"query": "주거 지원", "count": 25},
    ...
  ]
}
```

---

## 💻 PyCharm 실행 (Windows)

### 방법 1: Run Configuration 설정

1. **크롤링 스크립트 실행 설정**
   - `Run` → `Edit Configurations...`
   - `+` → `Python`
   - Name: `크롤링 및 저장`
   - Script path: `C:\...\test\scripts\crawl_and_save.py`
   - Working directory: `C:\...\test`
   - 실행: `Ctrl + Shift + F10`

2. **API 서버 실행 설정**
   - Name: `FastAPI 서버`
   - Module name: `uvicorn`
   - Parameters: `src.api.main:app --reload --host 0.0.0.0 --port 8000`
   - Working directory: `C:\...\test`

### 방법 2: 터미널에서 직접 실행

PyCharm 하단 터미널에서:

```powershell
# 1. 크롤링
python scripts/crawl_and_save.py

# 2. API 서버
uvicorn src.api.main:app --reload
```

### 방법 3: 테스트 스크립트 실행

```powershell
# 크롤러 테스트
python scripts/test_crawler.py

# LLM 테스트 (API 키 필요)
python scripts/test_llm.py
```

---

## 📁 프로젝트 구조

```
test/
├── src/
│   ├── api/                    # FastAPI 서버
│   │   ├── __init__.py
│   │   └── main.py             # API 엔드포인트
│   ├── database/               # SQLAlchemy ORM
│   │   ├── __init__.py
│   │   ├── models.py           # 데이터 모델
│   │   ├── database.py         # DB 연결 및 세션
│   │   ├── repository.py       # CRUD 로직
│   │   └── crawler_adapter.py  # 크롤러 연동
│   └── crawlers/               # 웹 크롤러
│       ├── base_crawler.py
│       ├── bokjiro_crawler.py
│       ├── kinfa_crawler.py
│       └── utils.py
├── scripts/
│   ├── crawl_and_save.py       # 크롤링 + 저장
│   ├── test_crawler.py         # 크롤러 테스트
│   └── test_llm.py             # LLM 테스트
├── data/
│   └── youth_policy.db         # SQLite 데이터베이스
├── requirements.txt
├── .env
└── MVP_GUIDE.md (이 파일)
```

---

## 🐛 문제 해결

### 문제 1: `ModuleNotFoundError`

```bash
pip install -r requirements.txt --upgrade
```

### 문제 2: SQLite 파일을 찾을 수 없음

```bash
# data 폴더 생성
mkdir data

# 다시 실행
python scripts/crawl_and_save.py
```

### 문제 3: 포트 8000이 이미 사용 중

```bash
# 다른 포트로 실행
uvicorn src.api.main:app --port 8080
```

### 문제 4: Windows에서 asyncio 오류

스크립트에 이미 포함되어 있습니다:
```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

## ✅ 다음 단계

1. ✅ 크롤링 및 DB 저장
2. ✅ API 서버 실행
3. 🔲 프론트엔드 연결 (다음 작업)
4. 🔲 LLM 통합 (선택)
5. 🔲 배포 (Docker 등)

---

## 📚 참고 자료

- **FastAPI 문서**: https://fastapi.tiangolo.com/
- **SQLAlchemy 문서**: https://docs.sqlalchemy.org/
- **Uvicorn 문서**: https://www.uvicorn.org/

---

**MVP 버전 특징:**
- ✅ 간단한 구조 (SQLite만 사용)
- ✅ ORM 기반 (SQL 쿼리 불필요)
- ✅ RESTful API
- ✅ Swagger UI 제공
- ✅ 검색 기록 자동 저장
- ✅ Windows/PyCharm 친화적

**즐거운 개발 되세요! 🎉**
