/**
 * =============================================================================
 * 채팅 입력 컴포넌트
 * =============================================================================
 *
 * 사용자 입력을 받는 텍스트 영역과 전송 버튼을 제공합니다.
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

import React from 'react';
import '../styles/ChatInput.css';

/**
 * Props 인터페이스
 */
interface ChatInputProps {
  /** 입력값 */
  value: string;
  /** 입력값 변경 핸들러 */
  onChange: (value: string) => void;
  /** 전송 핸들러 */
  onSend: () => void;
  /** 키 입력 핸들러 */
  onKeyPress: (e: React.KeyboardEvent) => void;
  /** 비활성화 여부 */
  disabled?: boolean;
  /** 플레이스홀더 */
  placeholder?: string;
}

/**
 * 채팅 입력 컴포넌트
 *
 * @param props - 컴포넌트 props
 */
const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  onKeyPress,
  disabled = false,
  placeholder = '메시지를 입력하세요...'
}) => {
  return (
    <div className="chat-input-container">
      {/* 텍스트 입력 영역 */}
      <textarea
        className="chat-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={onKeyPress}
        disabled={disabled}
        placeholder={placeholder}
        rows={2}
      />

      {/* 전송 버튼 */}
      <button
        className="send-button"
        onClick={onSend}
        disabled={disabled || !value.trim()}
        title="전송"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          width="24"
          height="24"
        >
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
        </svg>
      </button>
    </div>
  );
};

export default ChatInput;
