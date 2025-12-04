<template>
    <div class="flex items-center gap-2 p-1 bg-gray-100 rounded-lg">
        <button
            @click="uiStore.switchToKnowledgeMode"
            :class="[
                'px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200',
                uiStore.isKnowledgeMode
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
            ]"
        >
            Knowledge
        </button>
        <button
            @click="uiStore.switchToAgentMode"
            :class="[
                'px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200',
                uiStore.isAgentMode
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
            ]"
        >
            Agent
        </button>
    </div>
</template>

<script setup>
import { useUIStore } from "@/stores/ui";

const uiStore = useUIStore();
</script>

