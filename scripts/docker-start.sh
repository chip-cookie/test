#!/bin/bash
# 청년 정책 추천 시스템 Docker 시작 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 청년 정책 추천 시스템 시작${NC}"
echo "=================================="

# 환경 변수 파일 확인
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다. .env.example을 복사합니다.${NC}"
    cp .env.example .env
    echo -e "${RED}❌ .env 파일을 수정하여 API 키를 설정하세요.${NC}"
    exit 1
fi

# 필수 환경 변수 확인
source .env

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" == "sk-your-openai-api-key-here" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY가 설정되지 않았습니다.${NC}"
    exit 1
fi

if [ -z "$PINECONE_API_KEY" ] || [ "$PINECONE_API_KEY" == "your-pinecone-api-key-here" ]; then
    echo -e "${RED}❌ PINECONE_API_KEY가 설정되지 않았습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 환경 변수 확인 완료${NC}"

# Docker Compose 실행
echo -e "\n${GREEN}📦 Docker 컨테이너 시작 중...${NC}"

# 프로파일 옵션 처리
PROFILE=""
if [ "$1" == "--with-qdrant" ]; then
    PROFILE="--profile qdrant"
    echo "   Qdrant 포함"
fi

if [ "$1" == "--production" ]; then
    PROFILE="--profile production"
    echo "   프로덕션 모드 (Nginx 포함)"
fi

docker-compose $PROFILE up -d --build

# 상태 확인
echo -e "\n${GREEN}📊 컨테이너 상태:${NC}"
docker-compose ps

# 헬스체크 대기
echo -e "\n${YELLOW}⏳ 서비스 시작 대기 중...${NC}"
sleep 10

# N8N 상태 확인
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/healthz | grep -q "200"; then
    echo -e "${GREEN}✅ N8N 서비스가 정상적으로 시작되었습니다.${NC}"
else
    echo -e "${RED}❌ N8N 서비스 시작에 실패했습니다.${NC}"
    echo "   로그 확인: docker-compose logs n8n"
    exit 1
fi

echo -e "\n${GREEN}🎉 시스템이 준비되었습니다!${NC}"
echo "=================================="
echo "N8N 웹 인터페이스: http://localhost:5678"
echo "Webhook URL: http://localhost:5678/webhook/youth-policy"
echo ""
echo "테스트 명령어:"
echo "  curl -X POST http://localhost:5678/webhook/youth-policy \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"userInput\": \"서울 29세 직장인, 연봉 4천만원, 대출 갈아타기 원해요\"}'"
echo ""
echo "로그 확인: docker-compose logs -f n8n"
echo "중지: docker-compose down"
