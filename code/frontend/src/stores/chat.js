import { defineStore } from "pinia";
import { ref } from "vue";
import { useConversationStore } from "./conversation";
import { useUIStore } from "./ui";

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
        const { content, files = [], mentionedDepartments = [] } = messageData;
        
        if (!conversationStore.currentConversationId) {
            await conversationStore.createNewConversation();
        }

        // 사용자 메시지 추가
        await conversationStore.addMessage(
            conversationStore.currentConversationId,
            {
                role: "user",
                content: content,
                files: files,
                mentionedDepartments: mentionedDepartments,
            }
        );

        // Assistant 응답 시뮬레이션 (실제로는 API 호출)
        isThinking.value = true;
        isStreaming.value = true;
        streamingContent.value = "";

        // 간단한 응답 시뮬레이션
        setTimeout(() => {
            isThinking.value = false;
            const response = "안녕하세요! 무엇을 도와드릴까요?";
            
            // 스트리밍 시뮬레이션
            let index = 0;
            const streamInterval = setInterval(() => {
                if (index < response.length) {
                    streamingContent.value += response[index];
                    index++;
                } else {
                    clearInterval(streamInterval);
                    // 최종 메시지 추가
                    conversationStore.addMessage(
                        conversationStore.currentConversationId,
                        {
                            role: "assistant",
                            content: response,
                            isStreaming: false,
                        }
                    );
                    isStreaming.value = false;
                    streamingContent.value = "";
                }
            }, 50);
        }, 1000);
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

