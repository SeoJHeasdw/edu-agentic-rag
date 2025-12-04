<template>
    <div class="flex flex-col h-full overflow-hidden">
        <!-- 빈 상태 (대화가 없을 때) -->
        <div
            v-if="messages.length === 0"
            class="flex-1 flex flex-col items-center justify-center px-6 py-12"
        >
            <div class="text-center max-w-2xl">
                <div class="mb-8">
                    <div
                        class="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-teal-500 to-blue-600 rounded-2xl flex items-center justify-center"
                    >
                        <span class="text-2xl">🤖</span>
                    </div>
                    <h2 class="text-2xl font-bold text-gray-900 mb-2">
                        AI 어시스턴트 데모
                    </h2>
                    <p class="text-gray-600">
                        안녕하세요! 이것은 AI 어시스턴트의 사고 과정을 보여주는
                        데모입니다.
                    </p>
                </div>
            </div>
        </div>

        <!-- 메시지 목록 -->
        <div
            v-else
            ref="messagesContainer"
            class="pt-6 pb-4 overflow-y-auto"
            style="contain: layout"
        >
            <MessageItem
                v-for="message in messages"
                :key="message.id"
                :message="message"
            />

            <!-- 하단 여백 -->
            <div class="h-4"></div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from "vue";
import { useConversationStore } from "@/stores/conversation";
import { useMockChatStore } from "@/stores/mockChat";
import MessageItem from "./MessageItem.vue";

const conversationStore = useConversationStore();
const mockChatStore = useMockChatStore();

// Auto-scroll functionality
const messagesContainer = ref(null);

const scrollToBottom = () => {
    nextTick(() => {
        if (messagesContainer.value) {
            messagesContainer.value.scrollTop =
                messagesContainer.value.scrollHeight;
        }
    });
};

// Watch for message changes and auto-scroll
watch(
    () => conversationStore.currentConversation?.messages,
    () => {
        scrollToBottom();
    },
    { deep: true }
);

// 현재 대화의 메시지
const messages = computed(() => {
    return conversationStore.currentConversation?.messages || [];
});
</script>

