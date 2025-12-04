import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useUIStore } from "./ui";

export const useConversationStore = defineStore("conversation", () => {
    const uiStore = useUIStore();
    
    // 대화 목록 (로컬 스토리지 기반)
    const conversations = ref([]);
    
    // 현재 선택된 대화 ID
    const currentConversationId = ref(null);
    
    // 검색어
    const searchQuery = ref("");
    
    // 로딩 상태
    const isLoading = ref(false);

    // 현재 대화 가져오기
    const currentConversation = computed(() => {
        return conversations.value.find(
            (c) => c.id === currentConversationId.value
        );
    });

    // 필터링된 대화 목록
    const filteredConversations = computed(() => {
        if (!searchQuery.value) {
            return conversations.value;
        }

        return conversations.value.filter(
            (conv) =>
                conv.title
                    .toLowerCase()
                    .includes(searchQuery.value.toLowerCase()) ||
                conv.messages.some((msg) =>
                    msg.content
                        .toLowerCase()
                        .includes(searchQuery.value.toLowerCase())
                )
        );
    });

    // 새 대화 생성
    const createNewConversation = async () => {
        try {
            isLoading.value = true;
            
            const newConv = {
                id: `conv-${Date.now()}`,
                title: "새 채팅",
                messages: [],
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
            };
            
            conversations.value.unshift(newConv);
            currentConversationId.value = newConv.id;
            
            // 로컬 스토리지에 저장
            saveToLocalStorage();
            
            return newConv;
        } catch (error) {
            console.error("Failed to create new conversation:", error);
            uiStore.setError("새 대화 생성에 실패했습니다.");
            throw error;
        } finally {
            isLoading.value = false;
        }
    };

    // 대화 선택
    const selectConversation = async (id) => {
        currentConversationId.value = id;
    };

    // 대화 삭제
    const deleteConversation = async (id) => {
        try {
            isLoading.value = true;
            
            const index = conversations.value.findIndex((c) => c.id === id);
            if (index > -1) {
                conversations.value.splice(index, 1);

                // 현재 대화가 삭제된 경우 새 대화 생성
                if (currentConversationId.value === id) {
                    if (conversations.value.length > 0) {
                        currentConversationId.value = conversations.value[0].id;
                    } else {
                        await createNewConversation();
                    }
                }
                
                // 로컬 스토리지에 저장
                saveToLocalStorage();
                
                uiStore.setSuccess("대화가 삭제되었습니다.");
            }
        } catch (error) {
            console.error("Failed to delete conversation:", error);
            uiStore.setError(`대화 삭제에 실패했습니다: ${error.message}`);
            throw error;
        } finally {
            isLoading.value = false;
        }
    };

    // 메시지 추가
    const addMessage = async (conversationId, message) => {
        const conv = conversations.value.find((c) => c.id === conversationId);
        if (conv) {
            const messageId = message.id || `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const messageWithId = {
                ...message,
                id: messageId,
                timestamp: message.timestamp || new Date().toISOString(),
            };
            
            conv.messages.push(messageWithId);
            conv.updatedAt = new Date().toISOString();
            
            // 로컬 스토리지에 저장
            saveToLocalStorage();
            
            return messageWithId.id;
        }
        return null;
    };

    // 메시지 업데이트
    const updateMessage = (conversationId, messageId, updatedData) => {
        const conv = conversations.value.find((c) => c.id === conversationId);
        if (conv) {
            const messageIndex = conv.messages.findIndex((m) => m.id === messageId);
            if (messageIndex !== -1) {
                conv.messages.splice(messageIndex, 1, {
                    ...conv.messages[messageIndex],
                    ...updatedData,
                });
                conv.updatedAt = new Date().toISOString();
                saveToLocalStorage();
            }
        }
    };

    // 로컬 스토리지에 저장
    const saveToLocalStorage = () => {
        try {
            localStorage.setItem('conversations', JSON.stringify(conversations.value));
        } catch (error) {
            console.error('Failed to save conversations to localStorage:', error);
        }
    };

    // 로컬 스토리지에서 불러오기
    const loadFromLocalStorage = () => {
        try {
            const saved = localStorage.getItem('conversations');
            if (saved) {
                conversations.value = JSON.parse(saved);
            }
        } catch (error) {
            console.error('Failed to load conversations from localStorage:', error);
        }
    };

    return {
        conversations,
        currentConversationId,
        searchQuery,
        isLoading,
        currentConversation,
        filteredConversations,
        createNewConversation,
        selectConversation,
        deleteConversation,
        addMessage,
        updateMessage,
        loadFromLocalStorage,
        saveToLocalStorage,
    };
});

