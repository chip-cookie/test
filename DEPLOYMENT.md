# 청년 정책 추천 시스템 - 배포 가이드

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [빠른 시작](#빠른-시작)
3. [상세 설정](#상세-설정)
4. [프로덕션 배포](#프로덕션-배포)
5. [모니터링](#모니터링)
6. [트러블슈팅](#트러블슈팅)

---

## 사전 요구사항

### 필수

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Node.js** 18+ (프론트엔드)
- **Python** 3.10+ (크롤러)

### API 키

| 서비스 | 발급 URL | 용도 |
|--------|----------|------|
| OpenAI | https://platform.openai.com/api-keys | LLM + 임베딩 |
| Groq | https://console.groq.com/keys | LLM (Llama) |
| Gemini | https://aistudio.google.com/app/apikey | LLM |

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd test
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일 편집:

```bash
# 필수 API 키
OPENAI_API_KEY=sk-your-key
GROQ_API_KEY=gsk-your-key
GEMINI_API_KEY=your-key

# N8N 설정
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=secure-password
```

### 3. Docker Compose 실행

```bash
# 기본 서비스 (N8N + PostgreSQL)
docker-compose up -d

# Vector DB (Qdrant) 포함
docker-compose --profile qdrant up -d

# 캐시 (Redis) 포함
docker-compose --profile cache up -d

# 전체 서비스
docker-compose --profile qdrant --profile cache up -d
```

### 4. 접속 확인

- **N8N**: http://localhost:5678
- **Qdrant**: http://localhost:6333/dashboard

---

## 상세 설정

### Vector DB (Qdrant)

```bash
# Qdrant 단독 실행
docker run -p 6333:6333 -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant

# 컬렉션 생성 (자동으로 생성되지만 수동 생성 시)
curl -X PUT http://localhost:6333/collections/youth-policy-kb \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    }
  }'
```

### 크롤러 실행

```bash
# 가상환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 전체 크롤링 + Vector DB 적재
python scripts/run_crawlers.py

# 특정 소스만
python scripts/run_crawlers.py --source kinfa

# 테스트 실행 (DB 적재 없음)
python scripts/run_crawlers.py --dry-run
```

### 프론트엔드 실행

```bash
cd frontend
npm install

# 개발 서버
npm run dev

# 프로덕션 빌드
npm run build
npm run preview
```

---

## 프로덕션 배포

### Docker 이미지 빌드

```bash
# N8N 커스텀 이미지
docker build -t youth-policy-n8n .

# 프론트엔드 이미지
cd frontend
docker build -t youth-policy-frontend .
```

### Nginx 리버스 프록시

```nginx
# /etc/nginx/sites-available/youth-policy

upstream n8n {
    server localhost:5678;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    # 프론트엔드
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    # API (N8N)
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://n8n;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Webhook
    location /webhook/ {
        proxy_pass http://n8n;
        proxy_set_header Host $host;
    }
}
```

### SSL 인증서 (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Systemd 서비스

```bash
# /etc/systemd/system/youth-policy.service

[Unit]
Description=Youth Policy Recommendation System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable youth-policy
sudo systemctl start youth-policy
```

---

## 모니터링

### 헬스 체크

```bash
# N8N
curl http://localhost:5678/healthz

# Qdrant
curl http://localhost:6333/health

# 시스템 대시보드 API
curl http://localhost:5678/webhook/system-status
```

### 로그 확인

```bash
# Docker 로그
docker-compose logs -f n8n
docker-compose logs -f qdrant

# 크롤러 로그
tail -f logs/crawler_$(date +%Y%m%d).log
```

### 메트릭스

대시보드 API 사용:

```python
from src.monitoring import create_default_dashboard

dashboard = create_default_dashboard()
status = await dashboard.get_system_status()
print(status)
```

### 알림 설정

Slack 웹훅 설정:

```python
from src.monitoring import AlertManager, AlertConfig

config = AlertConfig(
    slack_webhook_url="https://hooks.slack.com/services/...",
    enabled_channels=["slack"],
    min_level=AlertLevel.ERROR
)

alert_manager = AlertManager(config)
```

---

## 트러블슈팅

### 문제: N8N이 시작되지 않음

```bash
# 로그 확인
docker-compose logs n8n

# 권한 문제 해결
sudo chown -R 1000:1000 ./n8n
```

### 문제: Qdrant 연결 실패

```bash
# Qdrant 상태 확인
curl http://localhost:6333/health

# 컨테이너 재시작
docker-compose restart qdrant
```

### 문제: 임베딩 생성 실패

```bash
# API 키 확인
echo $OPENAI_API_KEY

# 테스트
curl https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-ada-002", "input": "test"}'
```

### 문제: 크롤링 실패

```bash
# 네트워크 확인
curl -I https://www.bokjiro.go.kr

# 프록시 설정 (필요시)
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

### 문제: 프론트엔드 빌드 오류

```bash
# 캐시 삭제
rm -rf node_modules package-lock.json
npm install

# TypeScript 오류 확인
npm run type-check
```

---

## 자동화된 배포 (CI/CD)

GitHub Actions를 통한 자동 배포가 설정되어 있습니다:

- `.github/workflows/ci.yml`

### 배포 트리거

```bash
# main 브랜치에 푸시 시 자동 배포
git push origin main

# 수동 배포
gh workflow run ci.yml
```

### 환경 변수 설정 (GitHub Secrets)

Settings → Secrets → Actions에서 설정:

- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `DEPLOY_SERVER` (서버 IP)
- `DEPLOY_KEY` (SSH 키)

---

## 백업 및 복원

### 데이터 백업

```bash
# PostgreSQL
docker-compose exec postgres pg_dump -U n8n n8n > backup.sql

# Qdrant
docker cp youth-policy-qdrant:/qdrant/storage ./qdrant_backup
```

### 데이터 복원

```bash
# PostgreSQL
docker-compose exec -T postgres psql -U n8n n8n < backup.sql

# Qdrant
docker cp ./qdrant_backup youth-policy-qdrant:/qdrant/storage
docker-compose restart qdrant
```

---

## 지원

- **이슈 리포트**: GitHub Issues
- **문서**: README.md
- **API 문서**: `/src/api/openapi.yaml`
