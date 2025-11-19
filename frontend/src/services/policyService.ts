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

import axios, { AxiosInstance, AxiosError } from 'axios';

/**
 * API 설정
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5678';
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 60000;

/**
 * Multi-LLM 응답 타입
 */
interface MultiLLMResponse {
  best_response: string;
  selected_provider: string;
  total_latency: number;
  evaluation_scores?: Record<string, number>;
}

/**
 * 추천 결과 타입
 */
export interface RecommendResult {
  content: string;
  provider?: string;
  latency?: number;
}

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
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // 요청 인터셉터
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 응답 인터셉터: 상세 오류 처리
    this.client.interceptors.response.use(
      (response) => {
        console.log(`[API] 응답: ${response.status}`);
        return response;
      },
      (error: AxiosError) => {
        if (error.code === 'ECONNABORTED') {
          console.error('[API] 요청 타임아웃');
        } else if (error.response) {
          console.error(`[API] 서버 오류: ${error.response.status}`);
        } else if (error.request) {
          console.error('[API] 네트워크 오류');
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * 정책 추천 요청
   *
   * Multi-LLM 응답 형식을 처리합니다.
   *
   * @param userInput - 사용자 입력
   * @returns 추천 결과 (콘텐츠, 제공자, 지연시간)
   */
  async recommend(userInput: string): Promise<RecommendResult> {
    const response = await this.client.post<string | MultiLLMResponse>(
      '/webhook/youth-policy',
      { userInput }
    );

    const data = response.data;

    // Multi-LLM 응답 형식인 경우
    if (typeof data === 'object' && 'best_response' in data) {
      return {
        content: data.best_response,
        provider: data.selected_provider,
        latency: data.total_latency
      };
    }

    // 일반 문자열 응답
    return {
      content: typeof data === 'string' ? data : JSON.stringify(data)
    };
  }

  /**
   * 헬스체크
   *
   * @returns 시스템 상태
   */
  async healthCheck(): Promise<{ status: string; providers?: string[] }> {
    const response = await this.client.get('/healthz');
    return response.data;
  }

  /**
   * API 서버 상태 확인
   *
   * @returns 연결 가능 여부
   */
  async isAvailable(): Promise<boolean> {
    try {
      await this.healthCheck();
      return true;
    } catch {
      return false;
    }
  }
}

// 싱글톤 인스턴스 내보내기
export const policyService = new PolicyService();
