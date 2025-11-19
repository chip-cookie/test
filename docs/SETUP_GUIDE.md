# 📘 설정 가이드 (Setup Guide)

이 문서는 청년 정책 추천 시스템을 처음부터 설치하고 설정하는 상세한 가이드입니다.

---

## 목차

1. [사전 준비](#1-사전-준비)
2. [N8N 설치 및 설정](#2-n8n-설치-및-설정)
3. [Vector Database 설정](#3-vector-database-설정)
4. [OpenAI API 설정](#4-openai-api-설정)
5. [워크플로 Import 및 설정](#5-워크플로-import-및-설정)
6. [데이터 삽입](#6-데이터-삽입)
7. [테스트 및 검증](#7-테스트-및-검증)
8. [운영 환경 배포](#8-운영-환경-배포)
9. [문제 해결](#9-문제-해결)

---

## 1. 사전 준비

### 1.1 시스템 요구사항

- **OS**: Linux, macOS, Windows (WSL 권장)
- **Node.js**: v18.0.0 이상
- **npm**: v9.0.0 이상
- **메모리**: 최소 2GB RAM
- **디스크**: 최소 5GB 여유 공간

### 1.2 필수 계정

다음 서비스 계정을 미리 생성하세요:

1. **OpenAI**: https://platform.openai.com/signup
2. **Pinecone** (또는 다른 Vector DB): https://www.pinecone.io/start/

### 1.3 Node.js 설치 확인

```bash
node --version  # v18.0.0 이상
npm --version   # v9.0.0 이상
```

설치되지 않았다면:

```bash
# NVM을 통한 설치 (권장)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

---

## 2. N8N 설치 및 설정

### 2.1 N8N 전역 설치

```bash
npm install -g n8n
```

### 2.2 N8N 실행 확인

```bash
n8n start
```

브라우저에서 `http://localhost:5678` 접속하여 설치 확인

### 2.3 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```bash
# N8N 기본 설정
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your-secure-password

# Webhook 설정
WEBHOOK_URL=http://localhost:5678/
```

### 2.4 N8N 재시작

```bash
# .env 파일을 적용하여 재시작
n8n start
```

---

## 3. Vector Database 설정

### 3.1 Pinecone 설정 (권장)

#### Step 1: Pinecone 계정 생성
1. https://www.pinecone.io 접속
2. 무료 계정 생성 (Free tier: 1 index, 100K vectors)

#### Step 2: API Key 발급
1. Dashboard → API Keys → Create API Key
2. Key를 복사하여 안전하게 저장

#### Step 3: Index 생성

Pinecone 콘솔에서:
- Index name: `youth-policy-kb`
- Dimensions: `1536` (OpenAI text-embedding-ada-002)
- Metric: `cosine`
- Pod type: `s1.x1` (Free tier)

또는 API를 통해:

```bash
curl -X POST "https://api.pinecone.io/indexes" \
  -H "Api-Key: YOUR_PINECONE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "youth-policy-kb",
    "dimension": 1536,
    "metric": "cosine",
    "pod_type": "s1.x1"
  }'
```

#### Step 4: 환경 변수 추가

`.env` 파일에 추가:

```bash
# Pinecone 설정
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX=youth-policy-kb
```

### 3.2 대안: Qdrant 설정

Qdrant를 사용하려면:

```bash
# Docker로 Qdrant 실행
docker run -p 6333:6333 qdrant/qdrant

# 환경 변수 설정
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=youth-policy-kb
```

---

## 4. OpenAI API 설정

### 4.1 API Key 발급

1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. Key 이름 입력 (예: `youth-policy-system`)
4. Key를 복사하여 안전하게 저장

### 4.2 환경 변수 추가

`.env` 파일에 추가:

```bash
# OpenAI 설정
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### 4.3 비용 관리

OpenAI API 사용량 제한 설정:
1. https://platform.openai.com/account/billing/limits 접속
2. Monthly budget 설정 (예: $50)
3. Email notification 활성화

**예상 비용** (월 1000건 요청 기준):
- GPT-4 호출: ~$30
- Embedding 생성: ~$1
- **총 예상**: ~$31/월

---

## 5. 워크플로 Import 및 설정

### 5.1 N8N 워크플로 Import

1. N8N 웹 인터페이스 접속 (`http://localhost:5678`)
2. **Workflows** 탭 클릭
3. **Import from File** 클릭
4. `n8n/workflows/youth-policy-recommendation.json` 선택
5. **Import** 클릭

### 5.2 Credential 설정

#### OpenAI Credential

1. Import된 워크플로에서 OpenAI 노드 클릭
2. **Credential for OpenAI** → **Create New**
3. API Key 입력: `{{ $env.OPENAI_API_KEY }}`
4. **Save** 클릭

#### Pinecone Credential

1. Pinecone 노드 클릭
2. **Credential for Pinecone** → **Create New**
3. 설정:
   - API Key: `{{ $env.PINECONE_API_KEY }}`
   - Environment: `{{ $env.PINECONE_ENVIRONMENT }}`
4. **Save** 클릭

### 5.3 Webhook URL 확인

1. "Webhook Trigger" 노드 클릭
2. **Webhook URLs** 확인:
   - Production URL: `http://localhost:5678/webhook/youth-policy`
   - Test URL: `http://localhost:5678/webhook-test/youth-policy`

### 5.4 워크플로 활성화

1. 우측 상단 **Inactive** 토글 클릭 → **Active**로 변경
2. 워크플로가 활성화되면 Webhook이 실시간으로 요청을 받을 수 있습니다.

---

## 6. 데이터 삽입

### 6.1 Python 환경 설정

```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필요한 라이브러리 설치
pip install pinecone-client openai python-dotenv
```

### 6.2 데이터 삽입 스크립트

`scripts/insert_sample_data.py` 생성:

```python
import json
import os
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 초기화
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def insert_documents(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    vectors = []
    for doc in documents:
        embedding = create_embedding(doc['content'])
        vectors.append({
            'id': doc['id'],
            'values': embedding,
            'metadata': doc['metadata']
        })

    # Batch upsert
    index.upsert(vectors=vectors)
    print(f"✅ {len(vectors)} documents inserted from {file_path}")

if __name__ == "__main__":
    # Tier 1 데이터 삽입
    insert_documents("vector-db/sample-data/tier1-samples.json")

    # Tier 2 데이터 삽입
    insert_documents("vector-db/sample-data/tier2-samples.json")

    print("🎉 All sample data inserted successfully!")
```

### 6.3 스크립트 실행

```bash
python scripts/insert_sample_data.py
```

**출력 예시**:
```
✅ 5 documents inserted from vector-db/sample-data/tier1-samples.json
✅ 5 documents inserted from vector-db/sample-data/tier2-samples.json
🎉 All sample data inserted successfully!
```

### 6.4 데이터 확인

Pinecone 콘솔에서:
1. Index → `youth-policy-kb` 선택
2. **Stats** 탭: Vector count 확인 (총 10개)

---

## 7. 테스트 및 검증

### 7.1 기본 테스트

```bash
curl -X POST http://localhost:5678/webhook/youth-policy \
  -H "Content-Type: application/json" \
  -d '{
    "userInput": "서울 사는 29세 직장인이고, 연봉은 4천만 원이야. 지금 고금리 대출을 저금리 청년 대출로 갈아타고 싶어."
  }'
```

**예상 응답**: 마크다운 형식의 정책 추천 결과

### 7.2 테스트 케이스 실행

`tests/test-cases.json`에 정의된 11개 테스트 케이스 실행:

```bash
# 테스트 스크립트 (별도 제공)
python scripts/run_tests.py
```

### 7.3 N8N Execution Log 확인

1. N8N 웹 인터페이스 → **Executions** 탭
2. 최근 실행 기록 확인
3. 각 노드의 입력/출력 데이터 확인

---

## 8. 운영 환경 배포

### 8.1 Docker로 배포 (권장)

`Dockerfile` 생성:

```dockerfile
FROM n8nio/n8n:latest

# 환경 변수 설정
ENV N8N_HOST=0.0.0.0
ENV N8N_PORT=5678
ENV N8N_PROTOCOL=https

# 워크플로 복사
COPY n8n/workflows /root/.n8n/workflows

EXPOSE 5678

CMD ["n8n", "start"]
```

빌드 및 실행:

```bash
docker build -t youth-policy-n8n .
docker run -d -p 5678:5678 \
  --env-file .env \
  --name youth-policy-system \
  youth-policy-n8n
```

### 8.2 HTTPS 설정 (Nginx)

Nginx 설정:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Let's Encrypt SSL 인증서:

```bash
sudo certbot --nginx -d yourdomain.com
```

### 8.3 모니터링 설정

N8N Webhook 실패 알림:

1. N8N 워크플로에 "Error Trigger" 추가
2. 이메일 또는 Slack 알림 설정

---

## 9. 문제 해결

### 9.1 N8N 실행 오류

**문제**: `Error: Cannot find module 'n8n'`

**해결**:
```bash
npm uninstall -g n8n
npm install -g n8n
```

### 9.2 Pinecone 연결 오류

**문제**: `PineconeException: Unauthorized`

**해결**:
1. API Key 확인
2. Environment 이름 확인 (대소문자 구분)

### 9.3 OpenAI Rate Limit 오류

**문제**: `RateLimitError: You exceeded your current quota`

**해결**:
1. https://platform.openai.com/account/billing 접속
2. Payment method 추가
3. Usage limits 확인

### 9.4 Webhook 응답 없음

**문제**: curl 호출 시 응답 없음

**해결**:
1. N8N 워크플로가 **Active** 상태인지 확인
2. Webhook URL이 정확한지 확인
3. N8N Execution Log에서 오류 확인

---

## 완료!

모든 설정이 완료되었습니다. 이제 청년 정책 추천 시스템을 사용할 수 있습니다.

**다음 단계**:
1. 실제 정책 데이터 수집 및 삽입
2. 프론트엔드 UI 개발 (선택사항)
3. 정기적인 데이터 업데이트 자동화

**도움이 필요하신가요?**
- GitHub Issues: [프로젝트 이슈](https://github.com/yourusername/youth-policy-recommendation/issues)
- 이메일: support@example.com
