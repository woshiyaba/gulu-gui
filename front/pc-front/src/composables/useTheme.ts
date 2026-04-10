import { computed, ref } from 'vue'

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'lkwg-theme'
const theme = ref<ThemeMode>('light')

let initialized = false

function applyTheme(mode: ThemeMode) {
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.dataset.theme = mode
}

function setTheme(mode: ThemeMode) {
  theme.value = mode
  applyTheme(mode)

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(THEME_KEY, mode)
  }
}

function initTheme() {
  if (initialized) {
    return
  }

  initialized = true

  if (typeof window === 'undefined') {
    return
  }

  const savedTheme = window.localStorage.getItem(THEME_KEY)
  setTheme(savedTheme === 'dark' ? 'dark' : 'light')
}

export function useTheme() {
  initTheme()

  const isDark = computed(() => theme.value === 'dark')

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
  }
}
