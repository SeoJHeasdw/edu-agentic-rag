<template>
    <div>
        <!-- 메인 입력 영역 -->
        <div class="relative mb-6">
            <!-- 입력창 컨테이너 -->
            <div
                :class="[
                    'relative rounded-xl border transition-all duration-200',
                    isFocused
                        ? 'shadow-lg ring-2'
                        : 'shadow-sm hover:shadow-md',
                ]"
                :style="[
                    'background-color: var(--color-bg-primary)',
                    isFocused
                        ? 'border-color: var(--color-primary-300); box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); box-shadow: 0 0 0 2px var(--color-primary-50)'
                        : 'border-color: var(--color-border-light); box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
                    !isFocused && 'border-color: var(--color-border-light)'
                ]"
            >
                <!-- 텍스트 입력 영역 -->
                <div class="max-w-xl lg:max-w-2xl xl:max-w-3xl mx-auto w-full">
                    <div class="relative">
                        <textarea
                            ref="textareaRef"
                            v-model="message"
                            @input="handleInput"
                            @keydown="handleKeydown"
                            @focus="isFocused = true"
                            @blur="isFocused = false"
                            :placeholder="placeholder"
                            :disabled="chatStore.isStreaming"
                            class="w-full px-6 py-3 bg-transparent resize-none focus:outline-none min-h-[44px] max-h-[200px] placeholder-gray-400 text-gray-900 leading-relaxed whitespace-pre-wrap break-words chat-textarea"
                            rows="1"
                            style="
                                word-wrap: break-word;
                                overflow-wrap: break-word;
                            "
                        ></textarea>
                    </div>

                    <!-- 하단 버튼 영역 -->
                    <div class="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-t border-gray-100">
                        <!-- 왼쪽: 액션 버튼들 -->
                        <div class="flex items-center gap-2">
                            <!-- 파일 첨부 버튼 (+) -->
                            <button
                                :disabled="chatStore.isStreaming"
                                class="p-2 text-gray-500 hover:text-gray-700 disabled:opacity-50 transition-all duration-200 rounded-lg hover:bg-gray-100 border border-gray-200"
                                title="파일 첨부"
                            >
                                <svg
                                    class="w-5 h-5"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                                    />
                                </svg>
                            </button>
                        </div>

                        <!-- 오른쪽: 전송/중지 버튼 -->
                        <div class="flex items-center gap-2">
                            <!-- 전송 버튼 -->
                            <button
                                v-if="!chatStore.isStreaming"
                                @click="sendMessage"
                                :disabled="!canSend"
                                :class="[
                                    'px-4 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 text-sm font-medium',
                                    canSend
                                        ? 'bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 text-white shadow-sm hover:shadow-md'
                                        : 'bg-gray-200 text-gray-400 cursor-not-allowed',
                                ]"
                                title="전송 (Enter)"
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                                    />
                                </svg>
                                전송
                            </button>

                            <!-- 중지 버튼 -->
                            <button
                                v-else
                                @click="stopGeneration"
                                class="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2 text-sm font-medium"
                                title="생성 중지"
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M21 12H3"
                                    />
                                </svg>
                                중지
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 하단 정보 -->
            <div class="flex items-center justify-between mt-2 px-2">
                <div class="flex items-center gap-4 text-xs text-gray-400">
                    <span
                        v-if="chatStore.isStreaming"
                        class="flex items-center gap-2"
                    >
                        <div class="flex space-x-1">
                            <div
                                class="w-2 h-2 bg-teal-500 rounded-full animate-pulse"
                            ></div>
                            <div
                                class="w-2 h-2 bg-teal-500 rounded-full animate-pulse"
                                style="animation-delay: 0.2s"
                            ></div>
                            <div
                                class="w-2 h-2 bg-teal-500 rounded-full animate-pulse"
                                style="animation-delay: 0.4s"
                            ></div>
                        </div>
                        AI가 응답하고 있습니다...
                    </span>
                    <span v-else class="flex items-center gap-3">
                        <span class="flex items-center gap-1">
                            <kbd
                                class="px-1.5 py-0.5 bg-gray-100 rounded text-xs border border-gray-200 font-mono"
                                >Enter</kbd
                            >전송
                        </span>
                        <span class="flex items-center gap-1">
                            <kbd
                                class="px-1.5 py-0.5 bg-gray-100 rounded text-xs border border-gray-200 font-mono"
                                >Shift+Enter</kbd
                            >줄바꿈
                        </span>
                    </span>
                </div>

                <div class="flex items-center gap-3 text-xs text-gray-400">
                    <span>{{ message.length }}/4000</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from "vue";
import { useChatStore } from "@/stores/chat";

const chatStore = useChatStore();

const message = ref("");
const textareaRef = ref(null);
const isFocused = ref(false);

const placeholder = computed(() => {
    return chatStore.isStreaming
        ? "응답을 기다리는 중..."
        : "메시지를 입력하세요...";
});

const canSend = computed(() => {
    return (
        message.value.trim().length > 0 &&
        !chatStore.isStreaming
    );
});

// 텍스트 영역 높이 자동 조절
const adjustHeight = () => {
    if (textareaRef.value) {
        textareaRef.value.style.height = "auto";
        const scrollHeight = textareaRef.value.scrollHeight;
        const maxHeight = 200;
        const newHeight = Math.min(scrollHeight, maxHeight);

        textareaRef.value.style.height = newHeight + "px";

        if (scrollHeight > maxHeight) {
            textareaRef.value.style.overflowY = "auto";
        } else {
            textareaRef.value.style.overflowY = "hidden";
        }
    }
};

// 키보드 이벤트 처리
const handleKeydown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
};

// 텍스트 변경 감지
const handleInput = () => {
    adjustHeight();
};

// 메시지 전송
const sendMessage = () => {
    if (!canSend.value) return;

    const messageData = {
        content: message.value,
        files: chatStore.uploadedFiles,
    };

    chatStore.sendMessage(messageData);
    message.value = "";

    if (textareaRef.value) {
        textareaRef.value.style.height = "auto";
        textareaRef.value.style.overflowY = "hidden";
        textareaRef.value.focus();
    }
};

// 생성 중지
const stopGeneration = () => {
    chatStore.stopStreaming();
};

// 컴포넌트 마운트 시 초기화
onMounted(() => {
    nextTick(() => {
        if (textareaRef.value) {
            textareaRef.value.style.height = "auto";
            textareaRef.value.style.overflowY = "hidden";
            adjustHeight();
        }
    });
});
</script>

<style scoped>
/* 입력창 최대 너비 제한 및 가운데 정렬 */
.relative.mb-6 {
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
}

/* 반응형 최대 너비 */
@media (max-width: 1024px) {
    .relative.mb-6 {
        max-width: 500px;
    }
}

@media (max-width: 768px) {
    .relative.mb-6 {
        max-width: calc(100% - 2rem);
        margin-left: 1rem;
        margin-right: 1rem;
    }
}
</style>

