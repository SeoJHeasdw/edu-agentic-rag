import { marked } from 'marked'

// Marked 설정
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

// 마크다운을 HTML로 변환
export const parseMarkdown = (text) => {
  return marked.parse(text)
}

// 코드 블록 언어 감지
export const detectCodeLanguage = (code) => {
  // 간단한 언어 감지 로직
  if (code.includes('function') || code.includes('const') || code.includes('let')) {
    return 'javascript'
  }
  if (code.includes('def ') || code.includes('import ')) {
    return 'python'
  }
  if (code.includes('<html') || code.includes('<div')) {
    return 'html'
  }
  if (code.includes('public class') || code.includes('private ')) {
    return 'java'
  }
  return 'text'
}

