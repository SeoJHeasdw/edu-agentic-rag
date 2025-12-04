import { defineStore } from "pinia";
import { ref } from "vue";
import { useConversationStore } from "./conversation";
import { useUIStore } from "./ui";

export const useMockChatStore = defineStore("mockChat", () => {
    const conversationStore = useConversationStore();
    const uiStore = useUIStore();

    // 로딩 상태
    const isLoading = ref(false);

    // 메시지 전송 (Mock)
    const sendMessage = async (messageData) => {
        const { content } = messageData;
        
        if (!conversationStore.currentConversationId) {
            await conversationStore.createNewConversation();
        }

        // 사용자 메시지 추가
        await conversationStore.addMessage(
            conversationStore.currentConversationId,
            {
                role: "user",
                content: content,
            }
        );

        // Mock 응답 생성
        isLoading.value = true;
        
        setTimeout(() => {
            const mockResponse = {
                breakpoints: [
                    {
                        id: "breakpoint-1",
                        status: "검색 중...",
                        content: "관련 정보를 검색하고 있습니다.",
                    },
                ],
                currentStatus: "분석 중",
                currentResponse: "",
                finalResponse: "이것은 Mock 응답입니다.",
                isThinking: false,
                isStreaming: false,
            };

            conversationStore.addMessage(
                conversationStore.currentConversationId,
                {
                    role: "assistant",
                    content: JSON.stringify(mockResponse),
                }
            );
            
            isLoading.value = false;
        }, 2000);
    };

    return {
        isLoading,
        sendMessage,
    };
});

