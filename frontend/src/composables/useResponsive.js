import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Composable для отслеживания размера экрана
 * @param {number} breakpoint - Точка перелома (по умолчанию 768)
 * @returns {{ isMobile: import('vue').Ref<boolean> }}
 */
export function useResponsive(breakpoint = 768) {
  const isMobile = ref(window.innerWidth <= breakpoint)

  const updateMobile = () => {
    isMobile.value = window.innerWidth <= breakpoint
  }

  onMounted(() => window.addEventListener('resize', updateMobile))
  onUnmounted(() => window.removeEventListener('resize', updateMobile))

  return { isMobile }
}
