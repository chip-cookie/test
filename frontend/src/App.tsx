/**
 * =============================================================================
 * 청년 정책 추천 챗봇 메인 앱
 * =============================================================================
 *
 * React 기반 챗봇 UI의 메인 컴포넌트입니다.
 *
 * 주요 기능:
 *   - 사용자 입력 처리
 *   - API 호출 및 응답 표시
 *   - 채팅 기록 관리
 *
 * Author: Youth Policy System Team
 * Version: 1.0.0
 * =============================================================================
 */

import React from 'react';
import ChatWindow from './components/ChatWindow';
import './styles/App.css';

/**
 * 메인 앱 컴포넌트
 *
 * 앱의 최상위 컴포넌트로, 전체 레이아웃을 관리합니다.
 */
const App: React.FC = () => {
  return (
    <div className="app">
      {/* 헤더 */}
      <header className="app-header">
        <h1>🎯 청년 정책 추천 시스템</h1>
        <p>AI가 맞춤형 청년 정책을 추천해드립니다</p>
      </header>

      {/* 메인 채팅 영역 */}
      <main className="app-main">
        <ChatWindow />
      </main>

      {/* 푸터 */}
      <footer className="app-footer">
        <p>
          © 2025 Youth Policy System |{' '}
          <a href="https://www.youthcenter.go.kr" target="_blank" rel="noopener noreferrer">
            온통청년
          </a>
        </p>
      </footer>
    </div>
  );
};

export default App;
