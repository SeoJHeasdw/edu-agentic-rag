<template>
    <div
        class="px-6 py-6 last:pb-4 group hover:bg-gray-50/50 transition-colors duration-200"
        style="border-bottom: 1px solid rgba(0, 0, 0, 0.05)"
    >
        <div class="max-w-xl lg:max-w-2xl xl:max-w-3xl mx-auto">
            <div class="flex gap-3">
                <!-- 아바타 -->
                <div class="flex-shrink-0 mt-1">
                    <div
                        v-if="message.role === 'assistant'"
                        class="w-7 h-7 rounded-full flex items-center justify-center"
                        style="
                            background: linear-gradient(
                                135deg,
                                var(--color-primary-500),
                                var(--color-primary-600)
                            );
                        "
                    >
                        <svg
                            class="w-3.5 h-3.5 text-white"
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
                    <div
                        v-else
                        class="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-white font-medium text-xs"
                    >
                        U
                    </div>
                </div>

                <!-- 메시지 내용 -->
                <div class="flex-1 min-w-0">
                    <!-- 역할 표시 -->
                    <div class="mb-2">
                        <span class="text-sm font-medium text-gray-700">
                            {{
                                message.role === "assistant"
                                    ? "AI Assistant"
                                    : "사용자"
                            }}
                        </span>
                    </div>

                    <!-- Mock Message Component (for JSON content) -->
                    <MockMessageComponent
                        v-if="isMockMessage"
                        :message="message"
                    />

                    <!-- Regular Message Content -->
                    <template v-else>
                        <!-- 메시지 텍스트 -->
                        <div
                            v-if="message.isThinking"
                            class="flex items-center gap-3 text-sm text-teal-600"
                        >
                            <div class="flex items-center justify-center">
                                <div
                                    class="w-5 h-5 border-2 border-teal-200 border-t-teal-500 rounded-full animate-spin"
                                ></div>
                            </div>
                            <div class="flex items-center">
                                <span class="animate-pulse">{{ message.content }}</span>
                                <span class="ml-1 animate-bounce">.</span>
                                <span
                                    class="ml-0.5 animate-bounce"
                                    style="animation-delay: 0.1s"
                                    >.</span
                                >
                                <span
                                    class="ml-0.5 animate-bounce"
                                    style="animation-delay: 0.2s"
                                    >.</span
                                >
                            </div>
                        </div>
                        <div
                            v-else
                            class="message-content prose prose-sm max-w-none text-gray-800 leading-relaxed"
                            v-html="parseMarkdownContent(message.content)"
                        ></div>
                    </template>

                    <!-- 시간 표시 -->
                    <div class="text-xs text-gray-400 mt-2">
                        {{ formatTime(message.timestamp) }}
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { parseMarkdown } from "@/utils/markdown";
import MockMessageComponent from "./MockMessageComponent.vue";

const props = defineProps({
    message: {
        type: Object,
        required: true,
    },
});

// Mock message detection (JSON content)
const isMockMessage = computed(() => {
    try {
        const parsed = JSON.parse(props.message.content);
        return (
            parsed &&
            typeof parsed === "object" &&
            (parsed.breakpoints ||
                parsed.currentStatus ||
                parsed.currentResponse ||
                parsed.finalResponse)
        );
    } catch (error) {
        return false;
    }
});

// 마크다운 파싱 함수
const parseMarkdownContent = (content) => {
    return parseMarkdown(content);
};

// 시간 포맷팅
const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "방금 전";
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;

    return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
};
</script>

<style scoped>
/* 메시지 내용 스타일링 */
.message-content :deep(p) {
    @apply mb-3 last:mb-0 leading-relaxed;
}

.message-content :deep(pre) {
    @apply bg-gray-50 rounded-lg p-3 mb-3 overflow-x-auto border border-gray-200;
}

.message-content :deep(code) {
    @apply bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono;
}

.message-content :deep(pre code) {
    @apply bg-transparent p-0;
}

.message-content :deep(ul) {
    @apply list-disc pl-5 mb-3 space-y-1;
}

.message-content :deep(ol) {
    @apply list-decimal pl-5 mb-3 space-y-1;
}

.message-content :deep(blockquote) {
    @apply border-l-4 border-blue-300 pl-3 italic my-3 bg-blue-50 py-2 rounded-r-md;
}
</style>

