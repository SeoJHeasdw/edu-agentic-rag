<template>
    <div class="structured-message">
        <!-- Breakpoint Components -->
        <div
            v-if="
                messageComponents.breakpoints &&
                messageComponents.breakpoints.length > 0
            "
            class="breakpoint-components"
        >
            <div
                v-for="(breakpoint, index) in messageComponents.breakpoints"
                :key="breakpoint.id"
                class="breakpoint-component"
            >
                <!-- Divider between breakpoint components (except for the first one) -->
                <div v-if="index > 0" class="breakpoint-divider"></div>

                <!-- Todo List Component -->
                <TodoListComponent
                    v-if="breakpoint.isTodoList && breakpoint.todoList"
                    :todos="breakpoint.todoList"
                />

                <!-- Regular Breakpoint Content -->
                <div v-else-if="breakpoint.content" class="breakpoint-content">
                    <!-- Status Header -->
                    <div v-if="breakpoint.status" class="breakpoint-status">
                        <div class="flex items-center gap-2">
                            <div class="status-indicator"></div>
                            <span class="status-text">{{ breakpoint.status }}</span>
                        </div>
                    </div>

                    <!-- Content -->
                    <div
                        class="search-result-content prose prose-xs max-w-none text-gray-700 leading-relaxed"
                        v-html="parseMarkdown(breakpoint.content)"
                    ></div>
                </div>
            </div>
        </div>

        <!-- Current Status (thinking style) -->
        <div
            v-if="messageComponents.currentStatus && messageComponents.isThinking"
            class="flex items-center gap-3 text-sm text-teal-600"
        >
            <div class="flex items-center justify-center">
                <div
                    class="w-5 h-5 border-2 border-teal-200 border-t-teal-500 rounded-full animate-spin"
                ></div>
            </div>
            <div class="flex items-center">
                <span class="animate-pulse">{{ messageComponents.currentStatus }}</span>
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

        <!-- Streaming Response -->
        <div
            v-if="messageComponents.currentResponse"
            class="message-content prose prose-sm max-w-none text-gray-800 leading-relaxed"
            v-html="parseMarkdown(messageComponents.currentResponse)"
        ></div>

        <!-- Final Response -->
        <div v-if="messageComponents.finalResponse" class="final-response-container">
            <div class="breakpoint-divider"></div>
            <div
                class="message-content prose prose-sm max-w-none text-gray-800 leading-relaxed"
                v-html="parseMarkdown(messageComponents.finalResponse)"
            ></div>
        </div>
    </div>
</template>

<script setup>
import { computed } from "vue";
import { parseMarkdown } from "@/utils/markdown";
import TodoListComponent from "./TodoListComponent.vue";

const props = defineProps({
    message: {
        type: Object,
        required: true,
    },
});

const messageComponents = computed(() => {
    try {
        return JSON.parse(props.message.content);
    } catch (error) {
        return {
            breakpoints: [],
            currentStatus: "",
            currentResponse: "",
            finalResponse: props.message.content,
            isThinking: props.message.isThinking,
            isStreaming: props.message.isStreaming,
        };
    }
});
</script>

<style scoped>
.structured-message {
    @apply space-y-4;
}

.breakpoint-components {
    @apply space-y-3;
}

.breakpoint-component {
    @apply mb-4;
}

.breakpoint-divider {
    @apply my-3 border-t border-gray-200;
}

.breakpoint-content {
    @apply bg-gray-50 border border-gray-200 rounded-lg p-4;
}

.breakpoint-status {
    @apply mb-3 pb-2 border-b border-gray-200;
}

.status-indicator {
    @apply w-2 h-2 bg-teal-500 rounded-full animate-pulse;
}

.status-text {
    @apply text-sm font-medium text-teal-700;
}

.search-result-content {
    @apply text-xs;
}

.search-result-content :deep(p) {
    @apply mb-1 text-xs leading-relaxed;
}

.search-result-content :deep(strong) {
    @apply text-xs font-medium;
}
</style>


