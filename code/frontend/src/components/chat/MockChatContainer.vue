<template>
    <div
        class="flex flex-col h-full min-h-0 chat-container"
        style="background-color: var(--color-bg-primary)"
    >
        <!-- 메시지 리스트 - 고정 높이 보장 -->
        <div class="flex-1 min-h-0 overflow-hidden">
            <MockMessageList />
        </div>

        <!-- 입력 영역 -->
        <div class="w-full px-5">
            <MockChatInput />
        </div>
    </div>
</template>

<script setup>
import MockMessageList from "./MockMessageList.vue";
import MockChatInput from "./MockChatInput.vue";
</script>

