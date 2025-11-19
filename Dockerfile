# 청년 정책 추천 시스템 Dockerfile
# N8N + 커스텀 설정

FROM n8nio/n8n:latest

# 메타데이터
LABEL maintainer="Youth Policy System"
LABEL description="AI-based Youth Policy Recommendation System"
LABEL version="1.0.0"

# 환경 변수 기본값
ENV N8N_HOST=0.0.0.0
ENV N8N_PORT=5678
ENV N8N_PROTOCOL=http
ENV NODE_ENV=production
ENV EXECUTIONS_TIMEOUT=300000
ENV GENERIC_TIMEZONE=Asia/Seoul

# 작업 디렉토리
WORKDIR /home/node

# N8N 데이터 디렉토리 생성
RUN mkdir -p /home/node/.n8n/workflows

# 워크플로 파일 복사
COPY --chown=node:node n8n/workflows/*.json /home/node/.n8n/workflows/

# 포트 노출
EXPOSE 5678

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5678/healthz || exit 1

# 실행
USER node
CMD ["n8n", "start"]
