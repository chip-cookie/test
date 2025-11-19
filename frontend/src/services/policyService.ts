/**
 * =============================================================================
 * 정책 API 서비스
 * =============================================================================
 *
 * 백엔드 API와 통신하는 서비스 레이어입니다.
 * API 호출 로직을 캡슐화합니다.
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

import axios, { AxiosInstance } from 'axios';

/**
 * API 기본 URL
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5678';

/**
 * 정책 서비스 클래스
 *
 * 싱글톤 패턴으로 구현되어 앱 전체에서 하나의 인스턴스만 사용합니다.
 */
class PolicyService {
  /** Axios 인스턴스 */
  private readonly client: AxiosInstance;

  constructor() {
    // Axios 인스턴스 생성
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000, // 60초 (LLM 응답 시간 고려)
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // 응답 인터셉터: 오류 처리
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API 오류:', error);
        return Promise.reject(error);
      }
    );
  }

  /**
   * 정책 추천 요청
   *
   * @param userInput - 사용자 입력
   * @returns 마크다운 형식의 추천 결과
   */
  async recommend(userInput: string): Promise<string> {
    const response = await this.client.post<string>(
      '/webhook/youth-policy',
      { userInput }
    );

    return response.data;
  }

  /**
   * 헬스체크
   *
   * @returns 시스템 상태
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get('/healthz');
    return response.data;
  }
}

// 싱글톤 인스턴스 내보내기
export const policyService = new PolicyService();
