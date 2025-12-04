<template>
    <div class="todo-list-component">
        <div class="todo-header">
            <div class="flex items-center gap-2">
                <svg class="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="font-medium text-gray-800">할 일 목록</span>
            </div>
        </div>
        <div class="todo-items-container">
            <div
                v-for="item in todos"
                :key="item.id"
                class="todo-item"
                :class="{ completed: item.completed }"
            >
                <div class="todo-checkbox">
                    <div 
                        class="checkbox-circle"
                        :class="{ checked: item.completed }"
                    >
                        <svg 
                            v-if="item.completed"
                            class="w-3 h-3 text-white" 
                            fill="none" 
                            stroke="currentColor" 
                            viewBox="0 0 24 24"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                    </div>
                </div>
                <span class="todo-text">{{ item.text }}</span>
            </div>
        </div>
    </div>
</template>

<script setup>
const props = defineProps({
    todos: {
        type: Array,
        required: true,
    },
});
</script>

<style scoped>
.todo-list-component {
    @apply bg-white border border-gray-200 rounded-lg p-4 shadow-sm mb-4;
}

.todo-header {
    @apply mb-3 pb-2 border-b border-gray-100;
}

.todo-items-container {
    @apply space-y-0.5;
}

.todo-item {
    @apply flex items-center gap-3 py-1 px-3 rounded-md transition-all duration-200;
}

.todo-item:hover {
    @apply bg-gray-50;
}

.todo-item.completed {
    @apply opacity-60;
}

.todo-checkbox {
    @apply flex-shrink-0;
}

.checkbox-circle {
    @apply w-5 h-5 rounded-full border-2 border-gray-300 flex items-center justify-center transition-all duration-200;
}

.checkbox-circle.checked {
    @apply bg-teal-500 border-teal-500;
}

.todo-text {
    @apply text-sm text-gray-700 flex-1;
}

.todo-item.completed .todo-text {
    @apply line-through text-gray-500;
}
</style>

