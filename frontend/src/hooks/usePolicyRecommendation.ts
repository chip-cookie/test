/**
 * =============================================================================
 * 정책 추천 API 훅
 * =============================================================================
 *
 * 정책 추천 API를 호출하는 커스텀 훅입니다.
 * 로딩 상태, 오류 처리를 캡슐화합니다.
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

import { useState, useCallback } from 'react';
import { policyService, RecommendResult } from '../services/policyService';

/**
 * 반환 타입 인터페이스
 */
interface UsePolicyRecommendationReturn {
  /** 추천 요청 함수 */
  getRecommendation: (userInput: string) => Promise<string>;
  /** 로딩 상태 */
  isLoading: boolean;
  /** 오류 */
  error: Error | null;
  /** 마지막 응답의 제공자 정보 */
  lastProvider: string | null;
  /** 마지막 응답 지연 시간 */
  lastLatency: number | null;
}

/**
 * 정책 추천 커스텀 훅
 *
 * Multi-LLM 응답을 처리하고 최적의 결과를 반환합니다.
 *
 * @returns 추천 함수, 로딩 상태, 오류, 제공자 정보
 *
 * @example
 * const { getRecommendation, isLoading, lastProvider } = usePolicyRecommendation();
 *
 * const handleSubmit = async () => {
 *   const result = await getRecommendation(userInput);
 *   console.log(`응답 제공자: ${lastProvider}`);
 * };
 */
export const usePolicyRecommendation = (): UsePolicyRecommendationReturn => {
  // 상태
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastProvider, setLastProvider] = useState<string | null>(null);
  const [lastLatency, setLastLatency] = useState<number | null>(null);

  /**
   * 추천 요청 함수
   *
   * @param userInput - 사용자 입력
   * @returns 추천 결과 (마크다운)
   */
  const getRecommendation = useCallback(async (userInput: string): Promise<string> => {
    setIsLoading(true);
    setError(null);

    try {
      const result: RecommendResult = await policyService.recommend(userInput);

      // Multi-LLM 메타데이터 저장
      if (result.provider) {
        setLastProvider(result.provider);
      }
      if (result.latency) {
        setLastLatency(result.latency);
      }

      return result.content;

    } catch (err) {
      const error = err instanceof Error ? err : new Error('알 수 없는 오류');
      setError(error);
      throw error;

    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    getRecommendation,
    isLoading,
    error,
    lastProvider,
    lastLatency
  };
};
