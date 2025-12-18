<template>
    <div
        ref="scrollContainer"
        class="h-full overflow-y-auto"
        style="background-color: var(--color-bg-primary); contain: layout"
        @scroll="handleScroll"
    >
        <!-- 환영 메시지 -->
        <div
            v-if="!messages || messages.length === 0"
            class="h-full flex items-center justify-center"
        >
            <div
                class="text-center max-w-xl lg:max-w-2xl xl:max-w-3xl mx-auto px-6 pb-32"
            >
                <div class="mb-8">
                    <div
                        class="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-teal-400 to-emerald-500 flex items-center justify-center"
                    >
                        <svg
                            class="w-8 h-8 text-white"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M13 10V3L4 14h7v7l9-11h-7z"
                            />
                        </svg>
                    </div>
                    <h1 class="text-3xl font-semibold text-gray-900 mb-2">
                        안녕하세요!
                    </h1>
                    <p class="text-lg text-gray-600">무엇을 도와드릴까요?</p>
                </div>
            </div>
        </div>

        <!-- 메시지 목록 -->
        <div v-else class="pt-6 pb-4" style="contain: layout">
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
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { useConversationStore } from "@/stores/conversation";
import { useChatStore } from "@/stores/chat";
import MessageItem from "./MessageItem.vue";

const conversationStore = useConversationStore();
const chatStore = useChatStore();

const scrollContainer = ref(null);
const isUserScrolling = ref(false);
const lastScrollTop = ref(0);
let scrollTimeout = null;
let isAutoScrolling = ref(false);
let rafId = null;

// 현재 대화의 메시지
const messages = computed(() => {
    return conversationStore.currentConversation?.messages || [];
});

// 스크롤 함수
const scrollToBottom = (force = false) => {
    if (!scrollContainer.value) return;

    nextTick(() => {
        if (!scrollContainer.value) return;

        const container = scrollContainer.value;
        const shouldScroll = force || !isUserScrolling.value || isNearBottom();

        if (shouldScroll) {
            isAutoScrolling.value = true;

            container.scrollTo({
                top: container.scrollHeight,
                behavior: chatStore.isStreaming ? "auto" : "smooth",
            });

            setTimeout(() => {
                isAutoScrolling.value = false;
            }, 500);
        }
    });
};

// Throttled auto-scroll scheduler (prevents jitter during streaming)
const scheduleScroll = (force = false) => {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
        rafId = null;
        scrollToBottom(force);
    });
};

// 하단 근처인지 체크
const isNearBottom = () => {
    if (!scrollContainer.value) return true;

    const container = scrollContainer.value;
    const threshold = 50;
    return (
        container.scrollHeight - container.scrollTop - container.clientHeight <=
        threshold
    );
};

// 사용자 스크롤 감지
const handleScroll = () => {
    if (isAutoScrolling.value) return;

    if (!scrollContainer.value) return;

    const currentScrollTop = scrollContainer.value.scrollTop;

    if (currentScrollTop < lastScrollTop.value && !isNearBottom()) {
        isUserScrolling.value = true;
    } else if (isNearBottom()) {
        isUserScrolling.value = false;
    }

    lastScrollTop.value = currentScrollTop;

    if (scrollTimeout) {
        clearTimeout(scrollTimeout);
    }

    scrollTimeout = setTimeout(() => {
        // Don't force-follow again if user stopped mid-history; only reset when near bottom.
        if (isNearBottom()) {
            isUserScrolling.value = false;
        }
    }, 2000);
};

// 메시지 변경 감지
watch(
    () => messages.value.length,
    (newLength, oldLength) => {
        if (newLength > (oldLength || 0)) {
            setTimeout(() => {
                scheduleScroll(true);
            }, 50);
        }
    }
);

// 스트리밍/수정으로 마지막 메시지 내용이 계속 바뀌는 케이스도 따라가기
watch(
    () => messages.value[messages.value.length - 1]?.content,
    () => {
        if (!scrollContainer.value) return;
        if (!isUserScrolling.value || isNearBottom()) {
            scheduleScroll(false);
        }
    }
);

// 스트리밍 완료 시 스크롤
watch(
    () => chatStore.isStreaming,
    (isStreaming, wasStreaming) => {
        if (!isStreaming && wasStreaming) {
            nextTick(() => {
                scheduleScroll(true);
            });
        }
    }
);

onMounted(() => {
    nextTick(() => {
        scheduleScroll(true);
    });
});
</script>

