#!/usr/bin/env python3
"""
Vector Database에 청년 정책 샘플 데이터를 삽입하는 스크립트

사용법:
    python scripts/insert_sample_data.py --tier1 vector-db/sample-data/tier1-samples.json
    python scripts/insert_sample_data.py --all  # Tier 1과 Tier 2 모두 삽입
"""

import json
import os
import sys
import argparse
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Pinecone 설정
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "youth-policy-kb")

# OpenAI 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

# 기본 파일 경로
DEFAULT_TIER1_PATH = "vector-db/sample-data/tier1-samples.json"
DEFAULT_TIER2_PATH = "vector-db/sample-data/tier2-samples.json"


def check_dependencies():
    """필요한 라이브러리가 설치되어 있는지 확인"""
    missing = []

    try:
        from pinecone import Pinecone
    except ImportError:
        missing.append("pinecone-client")

    try:
        from openai import OpenAI
    except ImportError:
        missing.append("openai")

    if missing:
        print(f"❌ 필요한 라이브러리가 설치되지 않았습니다: {', '.join(missing)}")
        print(f"   설치: pip install {' '.join(missing)}")
        sys.exit(1)


def check_env_variables():
    """필요한 환경 변수가 설정되어 있는지 확인"""
    missing = []

    if not PINECONE_API_KEY:
        missing.append("PINECONE_API_KEY")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if missing:
        print(f"❌ 환경 변수가 설정되지 않았습니다: {', '.join(missing)}")
        print("   .env 파일을 생성하거나 환경 변수를 설정하세요.")
        sys.exit(1)


def create_embedding(client, text: str) -> List[float]:
    """OpenAI API를 사용하여 텍스트 임베딩 생성"""
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def load_documents(file_path: str) -> List[Dict[str, Any]]:
    """JSON 파일에서 문서 로드"""
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    print(f"📄 {len(documents)}개의 문서를 로드했습니다: {file_path}")
    return documents


def insert_documents(index, client, documents: List[Dict[str, Any]], batch_size: int = 10):
    """문서를 Vector DB에 삽입"""
    vectors = []
    total = len(documents)

    for i, doc in enumerate(documents, 1):
        print(f"   [{i}/{total}] 임베딩 생성 중: {doc['metadata']['policy_name'][:30]}...")

        # 임베딩 생성
        embedding = create_embedding(client, doc['content'])

        vectors.append({
            'id': doc['id'],
            'values': embedding,
            'metadata': doc['metadata']
        })

        # 배치 단위로 업서트
        if len(vectors) >= batch_size:
            index.upsert(vectors=vectors)
            vectors = []
            time.sleep(0.5)  # Rate limit 방지

    # 남은 벡터 업서트
    if vectors:
        index.upsert(vectors=vectors)

    print(f"✅ {total}개의 문서가 성공적으로 삽입되었습니다.")


def get_index_stats(index):
    """인덱스 통계 정보 출력"""
    stats = index.describe_index_stats()
    print(f"\n📊 인덱스 통계:")
    print(f"   - 총 벡터 수: {stats.total_vector_count}")
    print(f"   - 차원: {stats.dimension}")


def main():
    parser = argparse.ArgumentParser(
        description='Vector DB에 청년 정책 샘플 데이터 삽입'
    )
    parser.add_argument(
        '--tier1',
        type=str,
        help=f'Tier 1 데이터 파일 경로 (기본값: {DEFAULT_TIER1_PATH})'
    )
    parser.add_argument(
        '--tier2',
        type=str,
        help=f'Tier 2 데이터 파일 경로 (기본값: {DEFAULT_TIER2_PATH})'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Tier 1과 Tier 2 모두 삽입'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='배치 크기 (기본값: 10)'
    )

    args = parser.parse_args()

    # 환경 확인
    print("🔍 환경 확인 중...")
    check_dependencies()
    check_env_variables()

    # 라이브러리 import (환경 확인 후)
    from pinecone import Pinecone
    from openai import OpenAI

    # 클라이언트 초기화
    print("🔌 서비스 연결 중...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    print(f"   - Pinecone 인덱스: {PINECONE_INDEX}")
    print(f"   - 임베딩 모델: {EMBEDDING_MODEL}")

    # 삽입할 파일 결정
    files_to_insert = []

    if args.all:
        files_to_insert = [DEFAULT_TIER1_PATH, DEFAULT_TIER2_PATH]
    else:
        if args.tier1:
            files_to_insert.append(args.tier1)
        if args.tier2:
            files_to_insert.append(args.tier2)

        if not files_to_insert:
            # 인자가 없으면 기본적으로 Tier 1만 삽입
            files_to_insert = [DEFAULT_TIER1_PATH]

    # 데이터 삽입
    total_inserted = 0
    for file_path in files_to_insert:
        print(f"\n📥 데이터 삽입 시작: {file_path}")
        documents = load_documents(file_path)
        insert_documents(index, openai_client, documents, args.batch_size)
        total_inserted += len(documents)

    # 최종 통계
    get_index_stats(index)

    print(f"\n🎉 완료! 총 {total_inserted}개의 문서가 삽입되었습니다.")


if __name__ == "__main__":
    main()
