import { defineStore } from "pinia";
import { ref } from "vue";
import { useConversationStore } from "./conversation";
import { useUIStore } from "./ui";
import { sendChatMessage, sendStreamingChatMessage } from "@/utils/api";

export const useChatStore = defineStore("chat", () => {
    const conversationStore = useConversationStore();
    const uiStore = useUIStore();

    // 스트리밍 상태
    const isStreaming = ref(false);
    const isThinking = ref(false);
    const streamingContent = ref("");
    
    // 업로드된 파일들
    const uploadedFiles = ref([]);

    // 메시지 전송
    const sendMessage = async (messageData) => {
        const { content, files = [], mentionedDepartments = [], useStreaming = true } = messageData;
        
        if (!conversationStore.currentConversationId) {
            await conversationStore.createNewConversation();
        }

        const conversationId = conversationStore.currentConversationId;
        const currentConv = conversationStore.currentConversation;

        // 사용자 메시지 추가
        await conversationStore.addMessage(
            conversationId,
            {
                role: "user",
                content: content,
                files: files,
                mentionedDepartments: mentionedDepartments,
            }
        );

        // API 호출 준비
        isThinking.value = true;
        isStreaming.value = useStreaming;
        streamingContent.value = "";

        try {
            // 대화 히스토리 준비 (현재 메시지 제외)
            const historyMessages = currentConv?.messages
                ?.filter(msg => msg.role !== "user" || msg.content !== content)
                .map(msg => ({
                    role: msg.role,
                    content: msg.content,
                })) || [];

            if (useStreaming) {
                // 스트리밍 모드
                let fullResponse = "";

                await sendStreamingChatMessage(
                    content,
                    conversationId,
                    historyMessages,
                    (chunk) => {
                        // 청크 수신 시
                        isThinking.value = false;
                        fullResponse += chunk;
                        streamingContent.value = fullResponse;
                    },
                    (error) => {
                        // 에러 처리
                        console.error("Streaming error:", error);
                        uiStore.setError("메시지 전송 중 오류가 발생했습니다.");
                        isStreaming.value = false;
                        isThinking.value = false;
                    }
                );

                // 스트리밍 완료 후 최종 메시지 추가
                isStreaming.value = false;
                isThinking.value = false;
                await conversationStore.addMessage(
                    conversationId,
                    {
                        role: "assistant",
                        content: fullResponse,
                        isStreaming: false,
                    }
                );
                streamingContent.value = "";
            } else {
                // 일반 모드
                const response = await sendChatMessage(
                    content,
                    conversationId,
                    historyMessages
                );

                isThinking.value = false;
                await conversationStore.addMessage(
                    conversationId,
                    {
                        role: "assistant",
                        content: response.message,
                        isStreaming: false,
                    }
                );
            }
        } catch (error) {
            console.error("Error sending message:", error);
            uiStore.setError(error.message || "메시지 전송 중 오류가 발생했습니다.");
            isStreaming.value = false;
            isThinking.value = false;
            streamingContent.value = "";
        }
    };

    // 스트리밍 중지
    const stopStreaming = () => {
        isStreaming.value = false;
        isThinking.value = false;
        streamingContent.value = "";
    };

    // 파일 추가
    const addFile = (file) => {
        uploadedFiles.value.push(file);
    };

    // 파일 제거
    const removeFile = (index) => {
        uploadedFiles.value.splice(index, 1);
    };

    // 파일 목록 초기화
    const clearFiles = () => {
        uploadedFiles.value = [];
    };

    return {
        isStreaming,
        isThinking,
        streamingContent,
        uploadedFiles,
        sendMessage,
        stopStreaming,
        addFile,
        removeFile,
        clearFiles,
    };
});

