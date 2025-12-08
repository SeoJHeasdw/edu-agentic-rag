/**
 * API 유틸리티 함수
 * 백엔드 API 호출을 위한 헬퍼 함수
 */
import { API_ENDPOINTS } from '@/config/api';

/**
 * 일반 채팅 메시지 전송
 * @param {string} message - 사용자 메시지
 * @param {string|null} conversationId - 대화 ID (선택)
 * @param {Array} messages - 대화 히스토리 (선택)
 * @returns {Promise<Object>} 응답 데이터
 */
export async function sendChatMessage(message, conversationId = null, messages = []) {
    try {
        const response = await fetch(API_ENDPOINTS.CHAT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
                messages: messages.map(msg => ({
                    role: msg.role,
                    content: msg.content,
                })),
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error sending chat message:', error);
        throw error;
    }
}

/**
 * 스트리밍 채팅 메시지 전송
 * @param {string} message - 사용자 메시지
 * @param {string|null} conversationId - 대화 ID (선택)
 * @param {Array} messages - 대화 히스토리 (선택)
 * @param {Function} onChunk - 청크 수신 콜백 함수
 * @param {Function} onError - 에러 처리 콜백 함수
 * @returns {Promise<void>}
 */
export async function sendStreamingChatMessage(
    message,
    conversationId = null,
    messages = [],
    onChunk = () => {},
    onError = () => {}
) {
    try {
        const response = await fetch(API_ENDPOINTS.CHAT_STREAM, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                conversation_id: conversationId,
                messages: messages.map(msg => ({
                    role: msg.role,
                    content: msg.content,
                })),
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // 마지막 불완전한 라인은 버퍼에 보관

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    
                    if (data === '[DONE]') {
                        return;
                    }

                    try {
                        const parsed = JSON.parse(data);
                        onChunk(parsed.content || '', parsed);
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', data);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error sending streaming chat message:', error);
        onError(error);
        throw error;
    }
}

/**
 * API 헬스 체크
 * @returns {Promise<Object>} 헬스 상태
 */
export async function checkApiHealth() {
    try {
        const response = await fetch(API_ENDPOINTS.CHAT_HEALTH);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error checking API health:', error);
        throw error;
    }
}

