import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUIStore = defineStore('ui', () => {
  // 사이드바 상태
  const isSidebarOpen = ref(window.innerWidth >= 768)
  const isMobile = ref(window.innerWidth < 768)

  // 모드 상태 (Agent 모드 / Knowledge 모드)
  const currentMode = ref('knowledge') // 'knowledge' 또는 'agent'
  const isAgentMode = computed(() => currentMode.value === 'agent')
  const isKnowledgeMode = computed(() => currentMode.value === 'knowledge')

  // 로딩 상태
  const isLoading = ref(false)
  const loadingMessage = ref('')

  // 알림 상태
  const notification = ref(null)
  const notificationMessage = ref('')
  const notificationType = ref('error') // 'error' 또는 'success'

  // 모드 전환
  const switchToAgentMode = () => {
    currentMode.value = 'agent'
    localStorage.setItem('currentMode', 'agent')
  }

  const switchToKnowledgeMode = () => {
    currentMode.value = 'knowledge'
    localStorage.setItem('currentMode', 'knowledge')
  }

  const toggleMode = () => {
    if (currentMode.value === 'knowledge') {
      switchToAgentMode()
    } else {
      switchToKnowledgeMode()
    }
  }

  // 사이드바 토글
  const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value
    // 세션 저장
    localStorage.setItem('sidebarOpen', isSidebarOpen.value)
  }

  // 사이드바 상태 초기화
  const initSidebar = () => {
    const saved = localStorage.getItem('sidebarOpen')
    if (saved !== null) {
      isSidebarOpen.value = saved === 'true'
    } else {
      // 기본값: 데스크톱에서는 열림, 모바일에서는 닫힘
      isSidebarOpen.value = window.innerWidth >= 768
    }
  }

  // 모드 상태 초기화
  const initMode = () => {
    const saved = localStorage.getItem('currentMode')
    if (saved && (saved === 'agent' || saved === 'knowledge')) {
      currentMode.value = saved
    }
  }

  // 로딩 상태 설정
  const setLoading = (loading, message = '') => {
    isLoading.value = loading
    loadingMessage.value = message
  }

  // 알림 설정
  const setNotification = (message, type = 'error') => {
    notification.value = true
    notificationMessage.value = message
    notificationType.value = type

    // 자동 제거 (에러: 5초, 성공: 3초)
    const timeout = type === 'error' ? 5000 : 3000
    setTimeout(() => {
      notification.value = false
      notificationMessage.value = ''
    }, timeout)
  }

  // 에러 설정 (기존 호환성)
  const setError = (errorMsg) => {
    setNotification(errorMsg, 'error')
  }

  // 성공 메시지 설정
  const setSuccess = (successMsg) => {
    setNotification(successMsg, 'success')
  }

  // 알림 초기화
  const clearNotification = () => {
    notification.value = false
    notificationMessage.value = ''
  }

  // 화면 크기 체크
  const checkScreenSize = () => {
    isMobile.value = window.innerWidth < 768
    if (isMobile.value && isSidebarOpen.value) {
      isSidebarOpen.value = false
    }
  }

  return {
    isSidebarOpen,
    isMobile,
    currentMode,
    isAgentMode,
    isKnowledgeMode,
    isLoading,
    loadingMessage,
    notification,
    notificationMessage,
    notificationType,
    switchToAgentMode,
    switchToKnowledgeMode,
    toggleMode,
    toggleSidebar,
    initSidebar,
    initMode,
    setLoading,
    setNotification,
    setError,
    setSuccess,
    clearNotification,
    checkScreenSize
  }
})

