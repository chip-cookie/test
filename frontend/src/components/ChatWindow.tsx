/**
 * =============================================================================
 * 채팅 윈도우 컴포넌트
 * =============================================================================
 *
 * 채팅 UI의 핵심 컴포넌트입니다.
 * 메시지 목록, 입력창, 로딩 상태 등을 관리합니다.
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

import React, { useState, useRef, useEffect } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { usePolicyRecommendation } from '../hooks/usePolicyRecommendation';
import { Message } from '../types';
import '../styles/ChatWindow.css';

/**
 * 채팅 윈도우 컴포넌트
 *
 * 채팅 인터페이스의 메인 컨테이너입니다.
 * 메시지 상태 관리와 API 호출을 담당합니다.
 */
const ChatWindow: React.FC = () => {
  // ==========================================================================
  // 상태 관리
  // ==========================================================================

  // 메시지 목록
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'bot',
      content: `안녕하세요! 저는 청년 정책 추천 AI입니다. 🤖

다음과 같은 정보를 알려주시면 맞춤형 정책을 추천해드립니다:
- **나이**와 **거주 지역**
- **연소득** 또는 **직업 상태**
- **관심 있는 분야** (대출, 저축, 주거, 교육, 창업 등)

예: "서울 사는 29세 직장인이고, 연봉은 4천만 원이야. 대출 갈아타기에 관심 있어."`,
      timestamp: new Date()
    }
  ]);

  // 입력값
  const [inputValue, setInputValue] = useState('');

  // 스크롤 참조
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // API 호출 훅
  const { getRecommendation, isLoading, error } = usePolicyRecommendation();

  // ==========================================================================
  // 이펙트
  // ==========================================================================

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ==========================================================================
  // 이벤트 핸들러
  // ==========================================================================

  /**
   * 메시지 전송 처리
   *
   * 1. 사용자 메시지 추가
   * 2. API 호출
   * 3. 봇 응답 추가
   */
  const handleSendMessage = async () => {
    // 빈 입력 무시
    if (!inputValue.trim()) return;

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    try {
      // API 호출
      const response = await getRecommendation(inputValue);

      // 봇 응답 추가
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);

    } catch (err) {
      // 오류 메시지 추가
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: '죄송합니다. 요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        timestamp: new Date(),
        isError: true
      };

      setMessages(prev => [...prev, errorMessage]);
    }
  };

  /**
   * 엔터 키 처리
   */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ==========================================================================
  // 렌더링
  // ==========================================================================

  return (
    <div className="chat-window">
      {/* 메시지 목록 */}
      <div className="chat-messages">
        <MessageList messages={messages} />

        {/* 로딩 표시 */}
        {isLoading && (
          <div className="message bot loading">
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="loading-text">정책을 검색하고 있습니다...</span>
          </div>
        )}

        {/* 스크롤 앵커 */}
        <div ref={messagesEndRef} />
      </div>

      {/* 입력 영역 */}
      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSend={handleSendMessage}
        onKeyPress={handleKeyPress}
        disabled={isLoading}
        placeholder="정책에 대해 물어보세요..."
      />
    </div>
  );
};

export default ChatWindow;
