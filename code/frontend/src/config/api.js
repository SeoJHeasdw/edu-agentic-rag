/**
 * API Configuration
 * 백엔드 API 엔드포인트 설정
 */

// 개발 환경에서는 localhost, 프로덕션에서는 실제 백엔드 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const RAG_BASE_URL = import.meta.env.VITE_RAG_BASE_URL || 'http://localhost:8005';

export const API_ENDPOINTS = {
    CHAT: `${API_BASE_URL}/api/chat`,
    CHAT_STREAM: `${API_BASE_URL}/api/chat/stream`,
    CHAT_HEALTH: `${API_BASE_URL}/api/chat/health`,
    HEALTH: `${API_BASE_URL}/health`,
    RAG_INDEX_QDRANT_EMBEDDING_DOCS: `${RAG_BASE_URL}/rag/index/qdrant-embedding-docs`,
    RAG_HEALTH: `${RAG_BASE_URL}/health`,
};

export default {
    BASE_URL: API_BASE_URL,
    ENDPOINTS: API_ENDPOINTS,
};

