<template>
  <div class="h-screen flex overflow-hidden">
    <!-- 사이드바 -->
    <Sidebar />

    <!-- 메인 컨텐츠 -->
    <div class="flex-1 flex flex-col min-w-0 min-h-0">
      <!-- 메인 컨텐츠 영역 - 남은 공간 모두 사용 -->
      <main class="flex-1 min-h-0 overflow-hidden">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useUIStore } from '@/stores/ui'
import Sidebar from './Sidebar.vue'

const uiStore = useUIStore()

// 화면 크기 변경 감지
const handleResize = () => {
  uiStore.checkScreenSize()
}

onMounted(() => {
  uiStore.initSidebar()
  uiStore.initMode()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

