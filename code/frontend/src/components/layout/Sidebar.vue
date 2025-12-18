<template>
    <!-- 사이드바 (접힌/펼쳐진 상태 통합) -->
    <div
        class="fixed md:relative inset-y-0 left-0 z-40 flex flex-col shadow-sm transform transition-all duration-300 ease-in-out sidebar"
        :class="isCollapsed ? 'w-12' : 'w-80'"
        style="background-color: var(--color-bg-secondary); border-right: 1px solid var(--color-border-light)"
    >
        <!-- 접힌 상태일 때 아이콘들 -->
        <div v-if="isCollapsed" class="flex flex-col h-full">
            <!-- 상단 아이콘들 -->
            <div class="flex flex-col items-center py-4 space-y-2">
                <!-- 펼치기 버튼 -->
                <button
                    @click="toggleCollapse"
                    class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200"
                    title="사이드바 펼치기"
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
                            d="M4 6h16M4 12h16M4 18h16"
                        />
                    </svg>
                </button>

                <!-- 채팅 페이지 버튼 -->
                <router-link
                    to="/chat"
                    class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200"
                    :class="{ 'bg-primary-50 text-primary-600': $route.path === '/' || $route.path === '/chat' }"
                    title="채팅"
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
                            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                        />
                    </svg>
                </router-link>

                <!-- 관리 페이지 버튼 -->
                <router-link
                    to="/manage"
                    class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200"
                    :class="{ 'bg-primary-50 text-primary-600': $route.path === '/manage' }"
                    title="관리"
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
                            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                        />
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                    </svg>
                </router-link>

                <!-- 새 채팅 버튼 -->
                <button
                    @click="conversationStore.createNewConversation()"
                    class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200"
                    title="새 채팅"
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
                            d="M12 4v16m8-8H4"
                        />
                    </svg>
                </button>
            </div>

            <!-- 하단 아이콘들 -->
            <div
                class="mt-auto flex flex-col items-center pb-4 space-y-2 border-t border-gray-200 pt-2"
            >
                <!-- 사용자 아바타 -->
                <div
                    class="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center text-white font-medium text-xs"
                    title="사용자"
                >
                    U
                </div>
            </div>
        </div>

        <!-- 펼쳐진 상태일 때 전체 사이드바 -->
        <div v-else class="flex flex-col h-full">
            <!-- 공통 헤더 -->
            <div class="p-4 border-b border-gray-200">
                <div class="flex items-center justify-between mb-4">
                    <!-- 햄버거 메뉴 -->
                    <button
                        @click="toggleCollapse"
                        class="p-2 hover:bg-gray-100 rounded-lg transition-all duration-200"
                        title="사이드바 접기"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    </button>

                    <!-- 새 채팅 버튼 -->
                    <button
                        @click="conversationStore.createNewConversation()"
                        class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                        </svg>
                        새 채팅
                    </button>
                </div>

                <!-- 네비게이션 버튼들 -->
                <div class="flex gap-2">
                    <!-- 메인 채팅 버튼 -->
                    <router-link
                        to="/chat"
                        class="flex items-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 flex-1 justify-center"
                        :class="route.path === '/' || route.path === '/chat' ? 'bg-primary-50 text-primary-600 border border-primary-200' : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                        </svg>
                        채팅
                    </router-link>

                    <!-- 관리 버튼 -->
                    <router-link
                        to="/manage"
                        class="flex items-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 flex-1 justify-center"
                        :class="route.path === '/manage' ? 'bg-primary-50 text-primary-600 border border-primary-200' : 'text-gray-700 hover:text-gray-900 hover:bg-gray-100'"
                    >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        </svg>
                        관리
                    </router-link>
                </div>
            </div>

            <!-- 대화 목록 -->
            <div class="flex-1 overflow-y-auto">
                <div class="p-2">
                    <div
                        v-for="conv in conversationStore.filteredConversations"
                        :key="conv.id"
                        @click="handleConversationClick(conv.id)"
                        :class="[
                            'group flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-all duration-200',
                            conversationStore.currentConversationId === conv.id
                                ? 'bg-blue-50 text-blue-700' 
                                : 'hover:bg-gray-50 text-gray-700',
                        ]"
                    >
                        <!-- 대화 아이콘 -->
                        <div
                            :class="[
                                'flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center',
                                conversationStore.currentConversationId === conv.id
                                    ? 'bg-blue-100 text-blue-600'
                                    : 'bg-gray-100 text-gray-500',
                            ]"
                        >
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                        </div>

                        <!-- 대화 정보 -->
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-medium truncate">{{ conv.title }}</div>
                            <div class="text-xs text-gray-500 mt-0.5">{{ formatTime(conv.updatedAt) }}</div>
                        </div>

                        <!-- 액션 버튼들 -->
                        <div class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            <button
                                @click.stop="handleDelete(conv.id)"
                                class="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-all duration-200"
                                title="삭제"
                            >
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 공통 하단 사용자 영역 -->
            <div class="p-4 border-t border-gray-200">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center text-white font-medium text-sm">
                        U
                    </div>
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900">사용자</div>
                        <div class="text-xs text-gray-500">학습자</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 모바일 오버레이 -->
    <Transition
        enter-active-class="transition-opacity duration-300"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-300"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
    >
        <div
            v-if="isOpen && uiStore.isMobile"
            @click="uiStore.toggleSidebar()"
            class="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
        ></div>
    </Transition>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useConversationStore } from "@/stores/conversation";
import { useUIStore } from "@/stores/ui";

const conversationStore = useConversationStore();
const uiStore = useUIStore();
const route = useRoute();

const isCollapsed = ref(false);

const isOpen = computed(() => uiStore.isSidebarOpen);

// 사이드바 접기/펼치기
const toggleCollapse = () => {
    isCollapsed.value = !isCollapsed.value;
    localStorage.setItem("sidebarCollapsed", isCollapsed.value);
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
        month: "short",
        day: "numeric",
    });
};

// 대화 클릭 핸들러
const handleConversationClick = async (id) => {
    await conversationStore.selectConversation(id);
};

// 대화 삭제
const handleDelete = async (id) => {
    const conversation = conversationStore.conversations.find(c => c.id === id);
    const title = conversation?.title || '이 대화';
    
    if (confirm(`"${title}" 대화를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
        try {
            await conversationStore.deleteConversation(id);
        } catch (error) {
            console.error("Delete failed:", error);
        }
    }
};

// 컴포넌트 마운트 시 저장된 상태 복원
const restoreCollapsedState = () => {
    const saved = localStorage.getItem("sidebarCollapsed");
    if (saved !== null) {
        isCollapsed.value = saved === "true";
    }
};

// 초기화
onMounted(() => {
    restoreCollapsedState();
});
</script>

