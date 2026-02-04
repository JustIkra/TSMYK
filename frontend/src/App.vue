<template>
  <el-config-provider :locale="locale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import ru from 'element-plus/es/locale/lang/ru'

const locale = ref(ru)
</script>

<style>
@import url('./styles/theme-tokens.css');
@import url('./styles/animations.css');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
}

body {
  font-family: var(--font-family-base);
  background-color: var(--color-bg-page);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
}

/* Link styles */
a {
  color: var(--color-primary);
  text-decoration: none;
  transition: var(--transition-fast);
}

a:hover {
  color: var(--color-primary-dark);
}

/* Selection */
::selection {
  background-color: var(--color-primary-lighter);
  color: var(--color-text-primary);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--color-gray-100);
  border-radius: var(--border-radius-sm);
}

::-webkit-scrollbar-thumb {
  background: var(--color-gray-300);
  border-radius: var(--border-radius-sm);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-gray-400);
}

/* Actions group for table cells */
.actions-group {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.actions-group .el-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.actions-group .el-button :deep(.el-icon) {
  margin-right: var(--spacing-xs);
}

/* Vertical actions group */
.actions-group--vertical {
  flex-direction: column;
  align-items: stretch;
}

/* Element Plus global overrides */
.el-message-box {
  border-radius: var(--border-radius-xl) !important;
}

.el-notification {
  border-radius: var(--border-radius-lg) !important;
}

.el-loading-mask {
  background-color: rgba(255, 255, 255, 0.9);
}

.el-empty__description {
  color: var(--color-text-secondary);
}
</style>
