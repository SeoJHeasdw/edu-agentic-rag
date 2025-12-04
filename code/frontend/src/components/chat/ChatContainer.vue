<template>
  <div class="flex flex-col h-full min-h-0 chat-container" style="background-color: var(--color-bg-primary)">
    <!-- 메시지 리스트 - 고정 높이 보장 -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <MessageList />
    </div>

    <!-- 입력 영역 -->
    <div class="w-full px-5">
      <ChatInput />
    </div>
  </div>
</template>

<script setup>
import MessageList from './MessageList.vue'
import ChatInput from './ChatInput.vue'
</script>

