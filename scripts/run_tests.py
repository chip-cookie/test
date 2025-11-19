#!/usr/bin/env python3
"""
청년 정책 추천 시스템 테스트 실행 스크립트

사용법:
    python scripts/run_tests.py                    # 모든 테스트 실행
    python scripts/run_tests.py --case TC-001      # 특정 테스트 케이스 실행
    python scripts/run_tests.py --verbose          # 상세 출력
"""

import json
import os
import sys
import argparse
import time
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 설정
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5678/webhook/youth-policy")
TEST_CASES_PATH = "tests/test-cases.json"

# 색상 코드
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def load_test_cases(file_path: str) -> List[Dict[str, Any]]:
    """테스트 케이스 로드"""
    if not os.path.exists(file_path):
        print(f"{Colors.RED}❌ 테스트 케이스 파일을 찾을 수 없습니다: {file_path}{Colors.RESET}")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def send_request(user_input: str, timeout: int = 30) -> Dict[str, Any]:
    """Webhook에 요청 전송"""
    try:
        response = requests.post(
            WEBHOOK_URL,
            json={"userInput": user_input},
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )

        return {
            "status_code": response.status_code,
            "content": response.text,
            "elapsed": response.elapsed.total_seconds()
        }
    except requests.exceptions.Timeout:
        return {
            "status_code": 0,
            "content": "Request timeout",
            "elapsed": timeout,
            "error": "timeout"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "status_code": 0,
            "content": str(e),
            "elapsed": 0,
            "error": "connection_error"
        }


def validate_response(response: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
    """응답 검증"""
    result = {
        "passed": True,
        "checks": [],
        "warnings": []
    }

    # 기본 상태 코드 확인
    if response.get("status_code") != 200:
        result["passed"] = False
        result["checks"].append({
            "name": "HTTP Status",
            "passed": False,
            "expected": 200,
            "actual": response.get("status_code")
        })
        return result

    result["checks"].append({
        "name": "HTTP Status",
        "passed": True,
        "expected": 200,
        "actual": 200
    })

    content = response.get("content", "")

    # 마크다운 테이블 존재 확인
    has_table = "|" in content and "---" in content
    result["checks"].append({
        "name": "Markdown Table",
        "passed": has_table,
        "expected": True,
        "actual": has_table
    })
    if not has_table:
        result["passed"] = False

    # 예상 정책 확인
    expected_policies = test_case.get("expected_policies", [])
    if expected_policies:
        for policy in expected_policies:
            found = policy in content
            result["checks"].append({
                "name": f"정책 포함: {policy}",
                "passed": found,
                "expected": True,
                "actual": found
            })
            if not found:
                result["warnings"].append(f"예상 정책 '{policy}'이 응답에 포함되지 않음")

    # 공식 링크 존재 확인
    has_link = "http" in content or "https" in content
    result["checks"].append({
        "name": "공식 링크 포함",
        "passed": has_link,
        "expected": True,
        "actual": has_link
    })

    # 필수 서류 섹션 확인
    has_documents = "서류" in content or "증명" in content
    result["checks"].append({
        "name": "필수 서류 언급",
        "passed": has_documents,
        "expected": True,
        "actual": has_documents
    })

    # 종합 판정
    failed_checks = [c for c in result["checks"] if not c["passed"]]
    if len(failed_checks) > 2:  # 3개 이상 실패 시 테스트 실패
        result["passed"] = False

    return result


def print_test_result(
    test_case: Dict[str, Any],
    response: Dict[str, Any],
    validation: Dict[str, Any],
    verbose: bool = False
):
    """테스트 결과 출력"""
    tc_id = test_case.get("test_case_id", "Unknown")
    tc_name = test_case.get("test_name", "Unknown")

    # 결과 상태
    if validation["passed"]:
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}"
    else:
        status = f"{Colors.RED}❌ FAIL{Colors.RESET}"

    print(f"\n{Colors.BOLD}[{tc_id}] {tc_name}{Colors.RESET}")
    print(f"   상태: {status}")
    print(f"   응답 시간: {response.get('elapsed', 0):.2f}초")

    if verbose or not validation["passed"]:
        print(f"   {Colors.BLUE}검증 결과:{Colors.RESET}")
        for check in validation["checks"]:
            icon = "✓" if check["passed"] else "✗"
            color = Colors.GREEN if check["passed"] else Colors.RED
            print(f"      {color}{icon}{Colors.RESET} {check['name']}")

        if validation.get("warnings"):
            print(f"   {Colors.YELLOW}경고:{Colors.RESET}")
            for warning in validation["warnings"]:
                print(f"      ⚠️ {warning}")

    if verbose and response.get("content"):
        print(f"\n   {Colors.BLUE}응답 내용 (처음 500자):{Colors.RESET}")
        content_preview = response["content"][:500]
        for line in content_preview.split('\n'):
            print(f"      {line}")
        if len(response["content"]) > 500:
            print(f"      ... ({len(response['content']) - 500}자 더)")


def run_single_test(
    test_case: Dict[str, Any],
    verbose: bool = False
) -> bool:
    """단일 테스트 케이스 실행"""
    user_input = test_case.get("user_input", "")

    if not user_input:
        print(f"{Colors.YELLOW}⚠️ 테스트 케이스에 user_input이 없습니다.{Colors.RESET}")
        return False

    # 요청 전송
    response = send_request(user_input)

    # 응답 검증
    validation = validate_response(response, test_case)

    # 결과 출력
    print_test_result(test_case, response, validation, verbose)

    return validation["passed"]


def run_all_tests(
    test_cases: List[Dict[str, Any]],
    verbose: bool = False,
    specific_case: Optional[str] = None
) -> Dict[str, Any]:
    """모든 테스트 케이스 실행"""
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }

    # 특정 케이스 필터링
    if specific_case:
        test_cases = [
            tc for tc in test_cases
            if tc.get("test_case_id") == specific_case
        ]
        if not test_cases:
            print(f"{Colors.RED}❌ 테스트 케이스를 찾을 수 없습니다: {specific_case}{Colors.RESET}")
            return results

    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}청년 정책 추천 시스템 테스트{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"테스트 케이스 수: {len(test_cases)}")

    for test_case in test_cases:
        # user_input이 없는 테스트는 스킵 (예: 목업 데이터 테스트)
        if not test_case.get("user_input"):
            results["skipped"] += 1
            tc_id = test_case.get("test_case_id", "Unknown")
            print(f"\n{Colors.YELLOW}⏭️ [{tc_id}] 스킵 (user_input 없음){Colors.RESET}")
            continue

        results["total"] += 1

        passed = run_single_test(test_case, verbose)

        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

        # 테스트 간 간격
        time.sleep(1)

    return results


def print_summary(results: Dict[str, Any]):
    """테스트 요약 출력"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}테스트 요약{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

    total = results["total"]
    passed = results["passed"]
    failed = results["failed"]
    skipped = results["skipped"]

    if total > 0:
        pass_rate = (passed / total) * 100
    else:
        pass_rate = 0

    print(f"   총 테스트: {total}")
    print(f"   {Colors.GREEN}통과: {passed}{Colors.RESET}")
    print(f"   {Colors.RED}실패: {failed}{Colors.RESET}")
    print(f"   {Colors.YELLOW}스킵: {skipped}{Colors.RESET}")
    print(f"   통과율: {pass_rate:.1f}%")

    if failed == 0 and total > 0:
        print(f"\n{Colors.GREEN}🎉 모든 테스트가 통과했습니다!{Colors.RESET}")
    elif failed > 0:
        print(f"\n{Colors.RED}⚠️ {failed}개의 테스트가 실패했습니다.{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description='청년 정책 추천 시스템 테스트 실행'
    )
    parser.add_argument(
        '--case',
        type=str,
        help='특정 테스트 케이스 ID (예: TC-001)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='상세 출력'
    )
    parser.add_argument(
        '--url',
        type=str,
        help=f'Webhook URL (기본값: {WEBHOOK_URL})'
    )

    args = parser.parse_args()

    # URL 설정
    global WEBHOOK_URL
    if args.url:
        WEBHOOK_URL = args.url

    # 테스트 케이스 로드
    test_cases = load_test_cases(TEST_CASES_PATH)

    # 테스트 실행
    results = run_all_tests(test_cases, args.verbose, args.case)

    # 요약 출력
    print_summary(results)

    # 종료 코드
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
