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

    const looksLikeStructuredAgentPayload = (obj) => {
        return (
            obj &&
            typeof obj === "object" &&
            (Array.isArray(obj.breakpoints) ||
                typeof obj.currentStatus === "string" ||
                typeof obj.currentResponse === "string" ||
                typeof obj.finalResponse === "string")
        );
    };

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

        // assistant placeholder (전송 직후 UI가 바로 반응하도록)
        const assistantMessageId = await conversationStore.addMessage(conversationId, {
            role: "assistant",
            content: "생각 중...",
            isThinking: true,
            isStreaming: false,
        });

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
                let structuredPayload = null;

                await sendStreamingChatMessage(
                    content,
                    conversationId,
                    historyMessages,
                    (chunk, meta) => {
                        // 청크 수신 시
                        isThinking.value = false;

                        // 백엔드가 구조화된 payload를 보내는 경우(JSON)
                        if (looksLikeStructuredAgentPayload(meta)) {
                            structuredPayload = meta;
                            // streaming 상태도 같이 반영
                            structuredPayload.isThinking = false;
                            structuredPayload.isStreaming = true;

                            const jsonString = JSON.stringify(structuredPayload);
                            streamingContent.value = jsonString;
                            conversationStore.updateMessage(conversationId, assistantMessageId, {
                                content: jsonString,
                                isThinking: false,
                                isStreaming: true,
                            });
                            return;
                        }

                        // 일반 텍스트 스트리밍
                        fullResponse += chunk || "";
                        streamingContent.value = fullResponse;
                        conversationStore.updateMessage(conversationId, assistantMessageId, {
                            content: fullResponse.length ? fullResponse : "생각 중...",
                            isThinking: false,
                            isStreaming: true,
                        });
                    },
                    (error) => {
                        // 에러 처리
                        console.error("Streaming error:", error);
                        uiStore.setError("메시지 전송 중 오류가 발생했습니다.");
                        isStreaming.value = false;
                        isThinking.value = false;
                        conversationStore.updateMessage(conversationId, assistantMessageId, {
                            content: "오류가 발생했습니다. 다시 시도해주세요.",
                            isThinking: false,
                            isStreaming: false,
                        });
                    }
                );

                // 스트리밍 완료 후 최종 메시지 추가
                isStreaming.value = false;
                isThinking.value = false;

                // structured 응답이면 finalResponse 중심으로 마무리 플래그만 정리
                if (structuredPayload) {
                    structuredPayload.isThinking = false;
                    structuredPayload.isStreaming = false;
                    const jsonString = JSON.stringify(structuredPayload);
                    conversationStore.updateMessage(conversationId, assistantMessageId, {
                        content: jsonString,
                        isThinking: false,
                        isStreaming: false,
                    });
                } else {
                    conversationStore.updateMessage(conversationId, assistantMessageId, {
                        content: fullResponse,
                        isThinking: false,
                        isStreaming: false,
                    });
                }
                streamingContent.value = "";
            } else {
                // 일반 모드
                const response = await sendChatMessage(
                    content,
                    conversationId,
                    historyMessages
                );

                isThinking.value = false;
                conversationStore.updateMessage(conversationId, assistantMessageId, {
                    content: response.message,
                    isThinking: false,
                    isStreaming: false,
                });
            }
        } catch (error) {
            console.error("Error sending message:", error);
            uiStore.setError(error.message || "메시지 전송 중 오류가 발생했습니다.");
            isStreaming.value = false;
            isThinking.value = false;
            streamingContent.value = "";
            conversationStore.updateMessage(conversationId, assistantMessageId, {
                content: "오류가 발생했습니다. 다시 시도해주세요.",
                isThinking: false,
                isStreaming: false,
            });
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

