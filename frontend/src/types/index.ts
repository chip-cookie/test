/**
 * =============================================================================
 * 타입 정의
 * =============================================================================
 *
 * 프론트엔드에서 사용하는 타입들을 정의합니다.
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

/**
 * 채팅 메시지 인터페이스
 */
export interface Message {
  /** 메시지 고유 ID */
  id: string;

  /** 메시지 유형 (사용자/봇) */
  type: 'user' | 'bot';

  /** 메시지 내용 */
  content: string;

  /** 생성 시각 */
  timestamp: Date;

  /** 오류 여부 */
  isError?: boolean;
}

/**
 * 사용자 정보 인터페이스
 */
export interface UserInfo {
  /** 나이 */
  age?: number;

  /** 거주 지역 */
  location?: string;

  /** 연소득 */
  incomeAnnual?: number;

  /** 직업 상태 */
  employmentStatus?: string;

  /** 관심 분야 */
  interestAreas?: string[];
}

/**
 * API 응답 인터페이스
 */
export interface ApiResponse<T> {
  /** 데이터 */
  data: T;

  /** 성공 여부 */
  success: boolean;

  /** 오류 메시지 */
  error?: string;
}
