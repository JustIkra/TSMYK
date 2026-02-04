<template>
  <app-layout>
    <div class="admin-users-view">
      <header class="page-header">
        <h1 class="page-title">
          Управление пользователями
        </h1>
        <p class="page-subtitle">
          Одобрение новых пользователей, назначение админов и удаление учётных записей
        </p>
      </header>

      <section
        v-loading="adminStore.loading"
        class="card section-card"
      >
        <h3 class="section-title">
          Ожидают одобрения ({{ adminStore.pendingUsers.length }})
        </h3>

        <el-empty
          v-if="adminStore.pendingUsers.length === 0"
          description="Нет пользователей, ожидающих одобрения"
        />

        <el-table
          v-else
          :data="adminStore.pendingUsers"
          class="users-table"
          table-layout="fixed"
        >
          <el-table-column
            prop="email"
            label="Email"
          />
          <el-table-column
            label="Статус"
            width="140"
          >
            <template #default="{ row }">
              <span class="status-tag status-tag--pending">
                {{ getStatusLabel(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="Дата регистрации"
            width="180"
          >
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleDateString('ru-RU') }}
            </template>
          </el-table-column>
          <el-table-column
            label="Действия"
            width="160"
            align="center"
          >
            <template #default="{ row }">
              <div class="actions-column">
                <el-button
                  type="success"
                  size="small"
                  @click="handleApprove(row)"
                >
                  Одобрить
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section
        v-loading="adminStore.loading"
        class="card section-card"
      >
        <h3 class="section-title">
          Все пользователи ({{ allUsers.length }})
        </h3>

        <el-empty
          v-if="allUsers.length === 0"
          description="Пользователи не найдены"
        />

        <el-table
          v-else
          :data="allUsers"
          class="users-table"
          table-layout="fixed"
        >
          <el-table-column
            prop="email"
            label="Email"
          />
          <el-table-column
            label="Роль"
            width="150"
          >
            <template #default="{ row }">
              <span :class="['status-tag', getRoleTagClass(row.role)]">
                {{ getRoleLabel(row.role) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            label="Статус"
            width="140"
          >
            <template #default="{ row }">
              <span :class="['status-tag', getStatusTagClass(row.status)]">
                {{ getStatusLabel(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="Дата регистрации"
            width="180"
          >
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleDateString('ru-RU') }}
            </template>
          </el-table-column>
          <el-table-column
            label="Действия"
            width="200"
            align="center"
          >
            <template #default="{ row }">
              <div
                v-if="row.id === authStore.user?.id"
                class="actions-column"
              >
                <span class="status-tag status-tag--info">
                  Это вы
                </span>
              </div>
              <div
                v-else
                class="actions-column"
              >
                <el-button
                  v-if="row.role !== 'ADMIN'"
                  type="warning"
                  size="small"
                  @click="handleMakeAdmin(row)"
                >
                  В админы
                </el-button>
                <el-button
                  v-if="row.role === 'ADMIN'"
                  size="small"
                  @click="handleRevokeAdmin(row)"
                >
                  Снять админа
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click="handleDelete(row)"
                >
                  Удалить
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>
  </app-layout>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppLayout from '@/components/AppLayout.vue'
import { useAdminStore, useAuthStore } from '@/stores'
import { getRoleLabel, getStatusLabel } from '@/utils/labels'

const getRoleTagClass = (role) => {
  const classMap = {
    ADMIN: 'status-tag--primary',
    USER: 'status-tag--info'
  }
  return classMap[role] || 'status-tag--info'
}

const getStatusTagClass = (status) => {
  const classMap = {
    ACTIVE: 'status-tag--success',
    PENDING: 'status-tag--pending',
    BLOCKED: 'status-tag--danger'
  }
  return classMap[status] || 'status-tag--info'
}

const adminStore = useAdminStore()
const authStore = useAuthStore()

const allUsers = computed(() => adminStore.users)

const handleApprove = async (user) => {
  try {
    await adminStore.approveUser(user.id)
    ElMessage.success(`Пользователь ${user.email} одобрен`)
  } catch (error) {
    ElMessage.error(adminStore.error || 'Ошибка одобрения пользователя')
  }
}

const handleMakeAdmin = async (user) => {
  try {
    await adminStore.makeAdmin(user.id)
    ElMessage.success(`Пользователь ${user.email} назначен администратором`)
  } catch (error) {
    ElMessage.error(adminStore.error || 'Ошибка назначения прав администратора')
  }
}

const handleRevokeAdmin = async (user) => {
  try {
    await adminStore.revokeAdmin(user.id)
    ElMessage.success(`Права администратора сняты с ${user.email}`)
  } catch (error) {
    ElMessage.error(adminStore.error || 'Ошибка снятия прав администратора')
  }
}

const handleDelete = async (user) => {
  if (user.id === authStore.user?.id) {
    ElMessage.error('Нельзя удалить собственную учётную запись администратора')
    return
  }

  try {
    await ElMessageBox.confirm(
      `Вы уверены, что хотите удалить пользователя ${user.email}?`,
      'Подтверждение удаления',
      {
        confirmButtonText: 'Удалить',
        cancelButtonText: 'Отмена',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    await adminStore.deleteUser(user.id)
    ElMessage.success(`Пользователь ${user.email} удалён`)
  } catch (error) {
    if (error === 'cancel') {
      return
    }
    ElMessage.error(adminStore.error || 'Ошибка удаления пользователя')
  }
}

onMounted(async () => {
  try {
    await adminStore.fetchPendingUsers()
    await adminStore.fetchAllUsers()
  } catch (error) {
    ElMessage.error(adminStore.error || 'Ошибка загрузки пользователей')
  }
})
</script>

<style scoped>
.admin-users-view {
  max-width: var(--container-max-width);
  margin: 0 auto;
}

/* Section card styling */
.section-card {
  margin-bottom: var(--spacing-2xl);
}

.section-card .section-title {
  margin: 0 0 var(--spacing-lg) 0;
}

/* Actions column */
.actions-column {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  justify-content: center;
  padding: var(--spacing-xs) 0;
}

.actions-column .el-button {
  margin: 0;
}

/* Status tags with muted colors */
.status-tag {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  border-radius: var(--border-radius-sm);
  line-height: 1.4;
}

.status-tag--success {
  background-color: var(--color-success-light);
  color: var(--color-success);
}

.status-tag--pending {
  background-color: var(--color-warning-light);
  color: var(--color-warning);
}

.status-tag--danger {
  background-color: var(--color-danger-light);
  color: var(--color-danger);
}

.status-tag--info {
  background-color: var(--color-info-light);
  color: var(--color-info);
}

.status-tag--primary {
  background-color: var(--color-primary-bg);
  color: var(--color-primary);
}

/* Table styling */
.users-table {
  border-radius: var(--border-radius-lg);
  overflow: hidden;
}

:deep(.el-table) {
  --el-table-border-color: var(--color-border-light);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-lg);
}

:deep(.el-table::before) {
  display: none;
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-gray-50);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--color-border-light);
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid var(--color-border-lighter);
  color: var(--color-text-regular);
}

:deep(.el-table__body tr:hover > td.el-table__cell) {
  background-color: var(--color-gray-50);
}

:deep(.el-table__body tr:last-child td.el-table__cell) {
  border-bottom: none;
}

/* Empty state */
:deep(.el-empty) {
  padding: var(--spacing-3xl) var(--spacing-xl);
}

:deep(.el-empty__description) {
  color: var(--color-text-secondary);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .actions-column {
    flex-direction: column;
  }

  .actions-column .el-button {
    width: 100%;
  }
}
</style>
