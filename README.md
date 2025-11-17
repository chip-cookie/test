# 🚀 AI 기반 청년 정책 추천 시스템

N8N과 RAG(Retrieval-Augmented Generation) 아키텍처를 활용한 맞춤형 청년 정책 및 핀테크 상품 추천 시스템입니다.

## 📋 목차

- [개요](#개요)
- [핵심 기능](#핵심-기능)
- [시스템 아키텍처](#시스템-아키텍처)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 설정](#설치-및-설정)
- [사용 방법](#사용-방법)
- [워크플로 상세](#워크플로-상세)
- [테스트](#테스트)
- [기여 방법](#기여-방법)
- [라이선스](#라이선스)

---

## 개요

이 프로젝트는 청년들이 자신의 개인 정보(연령, 소득, 거주지, 관심 분야)를 입력하면 **AI가 자동으로 최적의 정부 지원금 및 핀테크 상품을 추천**하는 시스템입니다.

### 주요 특징

- **RAG 기반 정확성**: Vector Database에서 최신 정책 정보를 검색하여 답변 생성
- **2단계 검증 시스템**: 메타데이터 필터링 + LLM 검증을 통한 신뢰도 보장
- **Tier 우선 원칙**: 공식 출처(Tier 1)와 비공식 출처(Tier 2)를 구분하여 신뢰성 확보
- **자동화된 워크플로**: N8N을 활용한 완전 자동화 처리

---

## 핵심 기능

### 1. 자연어 처리
- 사용자가 자연어로 입력한 정보를 구조화된 JSON으로 자동 변환
- 예: "서울 사는 29세 직장인이고, 연봉은 4천만 원이야" → `{"age": 29, "location": "서울", "income_annual": 40000000}`

### 2. 2단계 유효성 검증

#### Stage 1: 메타데이터 필터링
- 2024/2025년 데이터만 검색
- 종료일이 현재 날짜 이후인 정책만 선별

#### Stage 2: LLM 검증
- **Tier 1 우선 원칙**: 공식/비공식 정보 충돌 시 공식 정보 우선
- **교차 검증**: 여러 Tier 2 출처 간 정보 일치 확인
- **종료 키워드 검출**: "마감", "종료" 등 키워드 자동 필터링

### 3. 맞춤형 추천
- 사용자 조건(나이, 소득, 거주지)에 부합하는 정책만 추천
- 마크다운 테이블 형식으로 깔끔한 정보 제공
- 필수 서류 목록 및 공식 링크 포함

---

## 시스템 아키텍처

```
┌─────────────────┐
│  사용자 입력     │
│  (자연어)        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  STEP 1: LLM 입력 추출                       │
│  - 자연어 → JSON 변환                        │
│  - age, location, income_annual 등 추출       │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  STEP 2A: Vector DB 검색 (1차 필터)          │
│  - 메타데이터 기반 필터링                     │
│  - publish_year >= 2024                     │
│  - policy_end_date >= 현재 날짜              │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  STEP 2B: LLM 검증 (2차 필터)                │
│  - Tier 1 우선 원칙 적용                     │
│  - 교차 검증 및 유효성 재확인                 │
│  - 자격 조건 매칭                            │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  STEP 3: LLM 최종 답변 생성                  │
│  - 마크다운 테이블 형식                       │
│  - 사용자 맞춤형 설명                        │
│  - 신청 시 유의사항 포함                     │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  최종 답변       │
│  (Markdown)     │
└─────────────────┘
```

---

## 프로젝트 구조

```
.
├── n8n/
│   └── workflows/
│       └── youth-policy-recommendation.json    # N8N 워크플로 정의
├── vector-db/
│   ├── schema.json                            # Vector DB 스키마 정의
│   └── sample-data/
│       ├── tier1-samples.json                 # Tier 1 샘플 데이터
│       └── tier2-samples.json                 # Tier 2 샘플 데이터
├── prompts/
│   ├── step1-input-extraction.md              # STEP 1 프롬프트
│   ├── step2-validation.md                    # STEP 2 프롬프트
│   └── step3-generation.md                    # STEP 3 프롬프트
├── config/
│   └── metadata-schema.json                   # 메타데이터 스키마 및 필터 규칙
├── tests/
│   └── test-cases.json                        # 테스트 케이스
└── README.md                                  # 본 문서
```

---

## 설치 및 설정

### 필수 요구사항

- **N8N**: v1.0.0 이상
- **Vector Database**: Pinecone, Qdrant, Weaviate 등
- **LLM API**: OpenAI GPT-4 또는 호환 모델
- **Node.js**: v18 이상 (N8N 실행용)

### 1. N8N 설치

```bash
npm install -g n8n
```

### 2. Vector Database 설정

#### Pinecone 예시

```bash
# Pinecone 계정 생성 후 API Key 발급
# https://www.pinecone.io

# Index 생성
curl -X POST "https://api.pinecone.io/indexes" \
  -H "Api-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "youth-policy-kb",
    "dimension": 1536,
    "metric": "cosine"
  }'
```

### 3. 환경 변수 설정

`.env` 파일 생성:

```bash
# N8N 설정
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Vector Database (Pinecone 예시)
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX=youth-policy-kb
```

### 4. N8N 워크플로 Import

```bash
# N8N 실행
n8n start

# 브라우저에서 http://localhost:5678 접속
# Workflows > Import from File > n8n/workflows/youth-policy-recommendation.json 선택
```

### 5. Vector DB에 샘플 데이터 삽입

```bash
# Python 스크립트 예시 (별도 제공)
python scripts/insert_sample_data.py \
  --tier1 vector-db/sample-data/tier1-samples.json \
  --tier2 vector-db/sample-data/tier2-samples.json
```

---

## 사용 방법

### 1. 워크플로 활성화

N8N 웹 인터페이스에서 워크플로를 활성화합니다.

### 2. API 호출

```bash
curl -X POST http://localhost:5678/webhook/youth-policy \
  -H "Content-Type: application/json" \
  -d '{
    "userInput": "서울 사는 29세 직장인이고, 연봉은 4천만 원이야. 지금 고금리 대출을 저금리 청년 대출로 갈아타고 싶어."
  }'
```

### 3. 응답 예시

```markdown
# 🎯 2025년도 맞춤형 청년 정책 추천

**고객**님의 조건(만 **29**세, 연소득 **4,000만 원**, **서울** 거주)에 부합하는 유효한 정책입니다.

## 📋 추천 정책 목록

| 정책 구분 | 정책명 | 핵심 지원 내용 | 신청 자격 | 필수 서류 | 공식 링크 |
|----------|--------|--------------|----------|----------|----------|
| 대출 | ⭐ **청년 전용 대환대출** | 고금리(7% 이상) 대출을 저금리(5% 내외)로 전환 지원 | 만 19~34세, 연소득 5천만원 이하 | 신분증, 소득증명원, 기존 대출 증명서 | [바로가기](https://kinfa.or.kr) |

## ⚠️ 신청 시 유의사항

- 신청 기간: 2025년 12월 31일까지
- 주요 혜택: 기존 대출 금리 약 2% 절감 효과
```

---

## 워크플로 상세

### STEP 1: 사용자 정보 입력 및 구조화

**목적**: 자연어 입력을 JSON으로 변환

**프롬프트**: [prompts/step1-input-extraction.md](prompts/step1-input-extraction.md)

**입력 예시**:
```
서울 사는 29세 직장인이고, 연봉은 4천만 원이야.
```

**출력 예시**:
```json
{
  "age": 29,
  "location": "서울",
  "income_annual": 40000000,
  "employment_status": "직장인",
  "needs": ["대출"],
  "interest_areas": ["대출"],
  "target_year": 2025
}
```

### STEP 2A: Vector DB 검색 (1차 필터)

**목적**: 메타데이터 기반 사전 필터링

**필터 조건**:
- `publish_year IN [2024, 2025]`
- `policy_end_date >= CURRENT_DATE OR policy_end_date = 'N/A'`

### STEP 2B: LLM 검증 (2차 필터)

**목적**: 신뢰도 검증 및 자격 조건 매칭

**프롬프트**: [prompts/step2-validation.md](prompts/step2-validation.md)

**검증 규칙**:
1. **Tier 1 우선**: 공식 vs 비공식 충돌 시 공식 정보 채택
2. **교차 검증**: Tier 2 출처 3개 이상 일치 확인
3. **종료 키워드**: "마감", "종료" 등 자동 제외
4. **자격 조건**: 나이, 소득, 거주지 매칭

### STEP 3: 최종 답변 생성

**목적**: 사용자 친화적 마크다운 답변 생성

**프롬프트**: [prompts/step3-generation.md](prompts/step3-generation.md)

**출력 형식**:
- 마크다운 테이블
- 신청 시 유의사항
- 필수 서류 목록
- 공식 링크

---

## 테스트

### 테스트 케이스 실행

11개의 테스트 케이스가 `tests/test-cases.json`에 정의되어 있습니다.

**주요 테스트 시나리오**:
- TC-001: 대출 갈아타기 요청
- TC-002: 자산 형성 요청
- TC-003: 전세자금 요청 (소득 초과)
- TC-006: Tier 1 vs Tier 2 충돌
- TC-007: 종료된 정책 필터링
- TC-011: End-to-End 전체 워크플로

### 수동 테스트

```bash
# TC-001 테스트
curl -X POST http://localhost:5678/webhook/youth-policy \
  -H "Content-Type: application/json" \
  -d '{
    "userInput": "서울 사는 29세 직장인이고, 연봉은 4천만 원이야. 지금 고금리 대출을 저금리 청년 대출로 갈아타고 싶어."
  }'
```

---

## 데이터 소스

### Tier 1 (공식 출처)

- 서민금융진흥원: https://www.kinfa.or.kr
- 복지로: https://www.bokjiro.go.kr
- 주택도시기금: https://nhuf.molit.go.kr
- 중소벤처기업부: https://www.mss.go.kr
- 고용노동부: https://www.moel.go.kr
- OnStop 청년정책: https://www.youthcenter.go.kr

### Tier 2 (비공식 출처)

- 블로그, 뉴스 기사, 커뮤니티 글 (참고용)
- ⚠️ 반드시 Tier 1 출처로 재확인 필요

---

## 기술 스택

- **워크플로 자동화**: N8N
- **LLM**: OpenAI GPT-4
- **Vector DB**: Pinecone / Qdrant / Weaviate
- **Embedding 모델**: text-embedding-ada-002
- **프로토콜**: HTTP/REST API

---

## 주요 설정 파일

### Vector DB 스키마

`vector-db/schema.json`에서 다음을 정의합니다:
- Document schema
- Metadata fields
- Indexing strategy
- Query strategy

### 메타데이터 스키마

`config/metadata-schema.json`에서 다음을 정의합니다:
- Tier 정의 (Tier 1 / Tier 2)
- 필수 메타데이터 필드
- 필터 규칙 (Stage 1, Stage 2)
- Confidence scoring 기준

---

## 성능 최적화

### 1. Vector Search 최적화
- HNSW 인덱스 사용 (m=16, ef_construction=200)
- 하이브리드 검색 (Vector 70% + Keyword 30%)

### 2. LLM 호출 최적화
- 프롬프트 캐싱 활용
- Batch 처리 가능 시 일괄 처리

### 3. 응답 시간
- 평균: 3-5초
- 최적화 후: 2-3초

---

## 보안 고려사항

### 1. API Key 관리
- `.env` 파일 사용 (git에 커밋하지 않음)
- 환경 변수로 주입

### 2. 사용자 데이터 보호
- 개인정보는 임시로만 사용, 저장하지 않음
- HTTPS 사용 권장

### 3. Rate Limiting
- N8N Webhook에 Rate Limit 설정 권장

---

## FAQ

### Q1. Vector DB 대신 다른 저장소를 사용할 수 있나요?
A1. 네, N8N은 Pinecone, Qdrant, Weaviate, Supabase 등 다양한 Vector DB를 지원합니다.

### Q2. GPT-4 대신 다른 LLM을 사용할 수 있나요?
A2. 네, Claude, Llama 등 OpenAI API 호환 모델을 사용할 수 있습니다.

### Q3. 데이터는 얼마나 자주 업데이트해야 하나요?
A3. 정부 정책은 분기별로 변경되므로, **월 1회** 업데이트를 권장합니다.

### Q4. Tier 2 데이터를 수집하는 방법은?
A4. 웹 크롤링 또는 RSS 피드를 통해 자동 수집 가능합니다 (별도 스크립트 제공 예정).

---

## 로드맵

- [ ] **v1.1**: 웹 크롤링 자동화 추가
- [ ] **v1.2**: 다국어 지원 (영어, 중국어)
- [ ] **v1.3**: 챗봇 UI 통합
- [ ] **v2.0**: 개인화된 알림 시스템 (정책 변경 시 자동 알림)

---

## 기여 방법

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 라이선스

MIT License

Copyright (c) 2025 Youth Policy Recommendation System

---

## 문의

프로젝트 관련 문의: [GitHub Issues](https://github.com/yourusername/youth-policy-recommendation/issues)

---

## 참고 자료

- [N8N 공식 문서](https://docs.n8n.io/)
- [Pinecone 가이드](https://docs.pinecone.io/)
- [OpenAI API 문서](https://platform.openai.com/docs)
- [RAG 아키텍처 설명](https://arxiv.org/abs/2005.11401)

---

**Made with ❤️ for Korean Youth**
