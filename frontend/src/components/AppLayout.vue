<template>
  <el-container class="app-layout">
    <el-header class="app-header">
      <div class="header-container">
        <div class="header-left">
          <div class="logo">
            <span class="logo-icon">ЦМ</span>
            <span class="logo-text">Цифровая модель УК</span>
          </div>
        </div>

        <div class="header-right">
        <el-menu
          mode="horizontal"
          :default-active="activeRoute"
          :ellipsis="false"
          class="main-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/participants">
            <el-icon><User /></el-icon>
            <span>Участники</span>
          </el-menu-item>

          <el-sub-menu
            v-if="authStore.isAdmin"
            index="admin"
          >
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>Админ</span>
            </template>
            <el-menu-item index="/admin/users">
              Пользователи
            </el-menu-item>
            <el-menu-item index="/admin/weights">
              Весовые таблицы
            </el-menu-item>
            <el-menu-item index="/admin/competencies">
              Словарь компетенций
            </el-menu-item>
            <el-menu-item index="/admin/metric-generate">
              AI Генерация
            </el-menu-item>
            <el-menu-item index="/admin/audit-log">
              Журнал аудита
            </el-menu-item>
          </el-sub-menu>
        </el-menu>

        <el-dropdown @command="handleUserCommand">
          <span class="user-dropdown">
            <el-icon><UserFilled /></el-icon>
            <span>{{ displayName }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                Профиль
              </el-dropdown-item>
              <el-dropdown-item command="settings">
                <el-icon><Setting /></el-icon>
                Настройки
              </el-dropdown-item>
              <el-dropdown-item
                divided
                command="logout"
              >
                <el-icon><SwitchButton /></el-icon>
                Выход
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        </div>
      </div>
    </el-header>

    <el-main class="app-main">
      <slot />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, UserFilled, Setting, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeRoute = computed(() => route.path)
const displayName = computed(() => authStore.user?.full_name || authStore.user?.email)

const handleMenuSelect = (index) => {
  router.push(index)
}

const handleUserCommand = async (command) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'settings') {
    router.push('/settings')
  } else if (command === 'logout') {
    try {
      await authStore.logout()
      ElMessage.success('Выход выполнен')
      router.push('/login')
    } catch (error) {
      ElMessage.error('Ошибка выхода')
    }
  }
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  background-color: var(--color-bg-page);
}

.app-header {
  background-color: var(--color-white);
  border-bottom: 1px solid var(--color-border-light);
  height: var(--header-height);
  box-shadow: var(--shadow-xs);
  position: sticky;
  top: 0;
  z-index: var(--z-index-sticky);
  padding: 0 var(--spacing-2xl);
}

.header-container {
  max-width: var(--container-max-width);
  margin: 0 auto;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--gradient-primary);
  border-radius: var(--border-radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-white);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-sm);
  letter-spacing: -0.02em;
  box-shadow: var(--shadow-sm);
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

/* Navigation Menu Styles */
.main-menu {
  border-bottom: none;
  background-color: transparent;
}

.main-menu :deep(.el-menu-item) {
  height: var(--header-height);
  line-height: var(--header-height);
  padding: 0 var(--spacing-lg);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  border-bottom: 2px solid transparent;
  transition: var(--transition-fast);
  margin: 0 var(--spacing-xs);
  border-radius: var(--border-radius-sm) var(--border-radius-sm) 0 0;
}

.main-menu :deep(.el-menu-item:hover) {
  background-color: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.main-menu :deep(.el-menu-item.is-active) {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  background-color: var(--color-primary-bg);
  font-weight: var(--font-weight-semibold);
}

.main-menu :deep(.el-sub-menu__title) {
  height: var(--header-height);
  line-height: var(--header-height);
  padding: 0 var(--spacing-lg);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  border-bottom: 2px solid transparent;
  transition: var(--transition-fast);
  margin: 0 var(--spacing-xs);
  border-radius: var(--border-radius-sm) var(--border-radius-sm) 0 0;
}

.main-menu :deep(.el-sub-menu__title:hover) {
  background-color: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.main-menu :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  background-color: var(--color-primary-bg);
  font-weight: var(--font-weight-semibold);
}

/* User Dropdown Styles */
.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-base);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  border: 1px solid var(--color-border-light);
  background-color: var(--color-white);
}

.user-dropdown:hover {
  background-color: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: var(--color-border);
}

.user-dropdown .el-icon {
  font-size: var(--font-size-base);
  color: var(--color-primary);
}

.user-dropdown .el-icon--right {
  font-size: var(--font-size-xs);
  margin-left: var(--spacing-xs);
  color: var(--color-text-placeholder);
}

.app-main {
  background-color: var(--color-bg-page);
  padding: var(--spacing-2xl);
  min-height: calc(100vh - var(--header-height));
}

/* Dropdown Menu Styling */
:deep(.el-dropdown-menu) {
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-xs);
}

:deep(.el-dropdown-menu__item) {
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--color-text-regular);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  border-radius: var(--border-radius-sm);
  margin: 2px 0;
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: var(--color-primary-bg);
  color: var(--color-primary);
}

:deep(.el-dropdown-menu__item--divided) {
  border-top-color: var(--color-border-light);
  margin-top: var(--spacing-sm);
  padding-top: var(--spacing-sm);
}

/* Submenu Popup Styling */
:deep(.el-menu--popup) {
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-xs);
  min-width: 200px;
}

:deep(.el-menu--popup .el-menu-item) {
  height: 40px;
  line-height: 40px;
  padding: 0 var(--spacing-md);
  color: var(--color-text-regular);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
  border-radius: var(--border-radius-sm);
  margin: 2px 0;
}

:deep(.el-menu--popup .el-menu-item:hover) {
  background-color: var(--color-primary-bg);
  color: var(--color-primary);
}

:deep(.el-menu--popup .el-menu-item.is-active) {
  color: var(--color-primary);
  background-color: var(--color-primary-bg);
  font-weight: var(--font-weight-semibold);
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 var(--spacing-lg);
  }

  .logo-text {
    display: none;
  }

  .header-right {
    gap: var(--spacing-sm);
  }

  .main-menu :deep(.el-menu-item),
  .main-menu :deep(.el-sub-menu__title) {
    padding: 0 var(--spacing-sm);
    margin: 0;
  }

  .user-dropdown span:not(.el-icon) {
    display: none;
  }

  .app-main {
    padding: var(--spacing-lg);
  }
}
</style>
