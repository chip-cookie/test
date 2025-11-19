/**
 * =============================================================================
 * 메시지 목록 컴포넌트
 * =============================================================================
 *
 * 채팅 메시지들을 렌더링합니다.
 * Markdown 형식의 봇 응답을 HTML로 변환합니다.
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../types';
import '../styles/MessageList.css';

/**
 * Props 인터페이스
 */
interface MessageListProps {
  /** 메시지 배열 */
  messages: Message[];
}

/**
 * 메시지 목록 컴포넌트
 *
 * @param props - 컴포넌트 props
 */
const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  /**
   * 시간 포맷팅
   */
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.type} ${message.isError ? 'error' : ''}`}
        >
          {/* 아바타 */}
          <div className="message-avatar">
            {message.type === 'user' ? '👤' : '🤖'}
          </div>

          {/* 메시지 내용 */}
          <div className="message-content">
            {message.type === 'bot' ? (
              // 봇 메시지는 Markdown 렌더링
              <ReactMarkdown
                components={{
                  // 링크를 새 탭에서 열기
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                  // 테이블 스타일링
                  table: ({ children }) => (
                    <div className="table-wrapper">
                      <table>{children}</table>
                    </div>
                  )
                }}
              >
                {message.content}
              </ReactMarkdown>
            ) : (
              // 사용자 메시지는 일반 텍스트
              <p>{message.content}</p>
            )}
          </div>

          {/* 타임스탬프 */}
          <div className="message-time">
            {formatTime(message.timestamp)}
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageList;
