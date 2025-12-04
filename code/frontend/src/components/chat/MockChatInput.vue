<template>
    <div>
        <!-- 메인 입력 영역 -->
        <div
            class="relative mb-6 max-w-xl lg:max-w-2xl xl:max-w-3xl mx-auto w-full"
        >
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
                    !isFocused && 'border-color: var(--color-border-light)',
                ]"
            >
                <!-- 텍스트 입력 영역 -->
                <div class="w-full">
                    <div class="relative">
                        <textarea
                            ref="textareaRef"
                            :value="message"
                            @input="handleInput"
                            @keydown="handleKeydown"
                            @focus="isFocused = true"
                            @blur="isFocused = false"
                            :placeholder="placeholder"
                            :disabled="isLoading"
                            autocomplete="off"
                            autocorrect="off"
                            autocapitalize="off"
                            spellcheck="false"
                            class="w-full px-6 py-3 bg-transparent resize-none focus:outline-none min-h-[44px] max-h-[200px] placeholder-gray-400 text-gray-900 leading-relaxed whitespace-pre-wrap break-words chat-textarea"
                            rows="1"
                            style="
                                word-wrap: break-word;
                                overflow-wrap: break-word;
                            "
                        ></textarea>
                    </div>
                </div>

                <!-- 하단 버튼 영역 -->
                <div
                    class="flex items-center justify-between px-4 py-2 bg-gray-50/50 border-t border-gray-100"
                >
                    <!-- 왼쪽: 액션 버튼들 -->
                    <div class="flex items-center gap-2">
                        <!-- 파일 첨부 버튼 (+) -->
                        <button
                            :disabled="isLoading"
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
                            v-if="!isLoading"
                            @click="handleSend"
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
                            class="px-4 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 text-sm font-medium bg-red-500 hover:bg-red-600 text-white shadow-sm hover:shadow-md"
                            title="중지"
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
                                    d="M6 6h12v12H6z"
                                />
                            </svg>
                            중지
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from "vue";
import { useMockChatStore } from "@/stores/mockChat";

const mockChatStore = useMockChatStore();

// 반응형 데이터
const message = ref("");
const isFocused = ref(false);
const textareaRef = ref(null);

// 컴포넌트 마운트 시 입력창 초기화
onMounted(() => {
    message.value = "";
    if (textareaRef.value) {
        textareaRef.value.value = "";
    }
});

// 계산된 속성
const canSend = computed(() => {
    return message.value.trim().length > 0 && !mockChatStore.isLoading;
});

const isLoading = computed(() => mockChatStore.isLoading);

const placeholder = computed(() => {
    if (mockChatStore.isLoading) {
        return "AI가 응답을 생성 중입니다...";
    }
    return "메시지를 입력하세요...";
});

// 입력 처리
const handleInput = async (event) => {
    message.value = event.target.value;
    await nextTick();
};

// 키보드 이벤트 처리
const handleKeydown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSend();
    }
};

// 메시지 전송
const handleSend = async () => {
    if (!canSend.value) return;

    // DOM에서 직접 값을 가져와서 잘림 방지
    const rawMessage = textareaRef.value ? textareaRef.value.value : message.value;
    const messageContent = rawMessage.trim();
    if (!messageContent) return;

    // 입력창 즉시 초기화
    message.value = "";
    
    await nextTick();
    
    if (textareaRef.value) {
        textareaRef.value.value = "";
        textareaRef.value.focus();
    }

    try {
        await mockChatStore.sendMessage({
            content: messageContent,
        });
    } catch (error) {
        console.error("Failed to send message:", error);
    }
};

// 중지 함수
const stopGeneration = () => {
    console.log("Stop generation requested (not implemented for mock chat)");
};
</script>

