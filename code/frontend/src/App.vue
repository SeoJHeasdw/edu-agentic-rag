<template>
  <router-view />
</template>

<script setup>
import { onMounted } from "vue";
import { useConversationStore } from "@/stores/conversation";

const conversationStore = useConversationStore();

onMounted(async () => {
    // 로컬 스토리지에서 대화 목록 로드
    conversationStore.loadFromLocalStorage();
});
</script>

