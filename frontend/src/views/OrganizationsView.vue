<template>
  <app-layout>
    <div class="organizations-view">
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">
            Организации
          </h1>
          <el-button
            type="primary"
            @click="showCreateDialog = true"
          >
            <el-icon><Plus /></el-icon>
            Добавить организацию
          </el-button>
        </div>
      </div>

      <div class="filter-card card">
        <el-form
          :inline="!isMobile"
          :model="searchForm"
        >
          <el-form-item label="Поиск">
            <el-input
              v-model="searchForm.query"
              placeholder="Название организации"
              clearable
              :style="isMobile ? 'width: 100%' : 'width: 300px'"
              @change="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </el-form>
      </div>

      <div
        v-loading="organizationsStore.loading"
        class="table-card card"
      >
        <!-- Desktop Table -->
        <el-table
          v-if="!isMobile"
          :data="organizationsStore.organizations"
          stripe
          table-layout="fixed"
        >
          <el-table-column
            label="Название"
          >
            <template #default="{ row }">
              <el-link
                type="primary"
                :underline="false"
                @click="viewOrganization(row.id)"
              >
                {{ row.name }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column
            prop="description"
            label="Описание"
            show-overflow-tooltip
          />
          <el-table-column
            prop="departments_count"
            label="Отделов"
            width="100"
            align="center"
          />
          <el-table-column
            prop="participants_count"
            label="Участников"
            width="120"
            align="center"
          />
          <el-table-column
            label="Действия"
            width="200"
            align="center"
          >
            <template #default="{ row }">
              <div class="actions-group">
                <el-button
                  type="primary"
                  size="small"
                  @click="viewOrganization(row.id)"
                >
                  Открыть
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  plain
                  @click="confirmDelete(row)"
                >
                  Удалить
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- Mobile Cards -->
        <div
          v-else
          class="org-cards"
        >
          <div
            v-for="org in organizationsStore.organizations"
            :key="org.id"
            class="org-card"
          >
            <div class="org-card__name">
              <el-link
                type="primary"
                :underline="false"
                @click="viewOrganization(org.id)"
              >
                {{ org.name }}
              </el-link>
            </div>
            <div class="org-card__info">
              <div class="org-card__field">
                <span class="field-label">Описание:</span>
                <span class="field-value">{{ org.description || '—' }}</span>
              </div>
              <div class="org-card__field">
                <span class="field-label">Отделов:</span>
                <span class="field-value">{{ org.departments_count }}</span>
              </div>
            </div>
            <div class="org-card__actions">
              <el-button
                type="primary"
                @click="viewOrganization(org.id)"
              >
                Открыть
              </el-button>
              <el-button
                type="danger"
                plain
                @click="confirmDelete(org)"
              >
                Удалить
              </el-button>
            </div>
          </div>

          <el-empty
            v-if="!organizationsStore.organizations.length && !organizationsStore.loading"
            description="Нет организаций"
            :image-size="120"
          >
            <el-button
              type="primary"
              @click="showCreateDialog = true"
            >
              Добавить организацию
            </el-button>
          </el-empty>
        </div>

        <!-- Desktop Pagination -->
        <div
          v-if="!isMobile"
          class="pagination"
        >
          <el-pagination
            v-model:current-page="searchForm.page"
            v-model:page-size="searchForm.size"
            :total="organizationsStore.pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="handleSearch"
            @size-change="handleSearch"
          />
        </div>

        <!-- Mobile Pagination -->
        <div
          v-else
          class="pagination pagination--mobile"
        >
          <el-pagination
            v-model:current-page="searchForm.page"
            v-model:page-size="searchForm.size"
            :total="organizationsStore.pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="prev, pager, next"
            small
            @current-change="handleSearch"
            @size-change="handleSearch"
          />
        </div>
      </div>

      <!-- Create Dialog -->
      <el-dialog
        v-model="showCreateDialog"
        title="Добавить организацию"
        :width="isMobile ? '95%' : '500px'"
      >
        <el-form
          ref="createFormRef"
          :model="createForm"
          :rules="createRules"
          label-position="top"
        >
          <el-form-item
            label="Название"
            prop="name"
          >
            <el-input
              v-model="createForm.name"
              placeholder="Введите название организации"
            />
          </el-form-item>
          <el-form-item
            label="Описание"
            prop="description"
          >
            <el-input
              v-model="createForm.description"
              type="textarea"
              :rows="3"
              placeholder="Описание (необязательно)"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCreateDialog = false">
            Отмена
          </el-button>
          <el-button
            type="primary"
            :loading="organizationsStore.loading"
            @click="handleCreate"
          >
            Создать
          </el-button>
        </template>
      </el-dialog>
    </div>
  </app-layout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { useOrganizationsStore } from '@/stores'
import { useResponsive } from '@/composables/useResponsive'

const router = useRouter()
const organizationsStore = useOrganizationsStore()
const { isMobile } = useResponsive()

const searchForm = reactive({
  query: '',
  page: 1,
  size: 20
})

const showCreateDialog = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  name: '',
  description: ''
})

const createRules = {
  name: [
    { required: true, message: 'Введите название', trigger: 'blur' },
    { min: 1, max: 255, message: 'От 1 до 255 символов', trigger: 'blur' }
  ]
}

const handleSearch = async () => {
  try {
    await organizationsStore.searchOrganizations(searchForm)
  } catch (error) {
    ElMessage.error('Ошибка загрузки организаций')
  }
}

const handleCreate = async () => {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await organizationsStore.createOrganization(createForm)
      ElMessage.success('Организация создана')
      showCreateDialog.value = false
      createForm.name = ''
      createForm.description = ''
      await handleSearch()
    } catch (error) {
      ElMessage.error(organizationsStore.error || 'Ошибка создания организации')
    }
  })
}

const viewOrganization = (id) => {
  router.push(`/organizations/${id}`)
}

const confirmDelete = (org) => {
  ElMessageBox.confirm(
    `Вы уверены, что хотите удалить организацию "${org.name}"? Все отделы также будут удалены.`,
    'Подтверждение удаления',
    {
      confirmButtonText: 'Удалить',
      cancelButtonText: 'Отмена',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await organizationsStore.deleteOrganization(org.id)
      ElMessage.success('Организация удалена')
      await handleSearch()
    } catch (error) {
      ElMessage.error(organizationsStore.error || 'Ошибка удаления организации')
    }
  }).catch(() => {})
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.organizations-view {
  max-width: var(--container-max-width);
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-card {
  margin-bottom: var(--spacing-xl);
  background-color: var(--color-bg-section);
}

.filter-card :deep(.el-form-item__label) {
  color: var(--color-text-regular);
  font-weight: var(--font-weight-medium);
}

.filter-card :deep(.el-form-item) {
  margin-bottom: 0;
}

.table-card {
  background-color: var(--color-bg-card);
}

.table-card :deep(.el-table) {
  --el-table-border-color: var(--color-border-light);
  --el-table-header-bg-color: var(--color-gray-50);
  --el-table-row-hover-bg-color: var(--color-gray-50);
  border-radius: var(--border-radius-lg);
  overflow: hidden;
}

.table-card :deep(.el-table th.el-table__cell) {
  background-color: var(--color-gray-50);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  border-bottom: 1px solid var(--color-border-light);
}

.table-card :deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid var(--color-border-lighter);
  color: var(--color-text-regular);
}

.table-card :deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background-color: var(--color-gray-50);
}

.table-card :deep(.el-table__body tr:hover > td.el-table__cell) {
  background-color: var(--color-bg-hover);
}

.actions-group {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-sm);
  align-items: center;
}

.actions-group .el-button {
  margin: 0;
}

.pagination {
  margin-top: var(--spacing-xl);
  display: flex;
  justify-content: flex-end;
}

.pagination--mobile {
  justify-content: center;
}

/* Mobile Card Styles */
.org-cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.org-card {
  width: 100%;
  background-color: var(--color-bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-lg);
  transition: var(--transition-base);
}

.org-card:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--color-border);
}

.org-card__name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.org-card__info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
}

.org-card__field {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.field-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.org-card__actions {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-sm);
}

.org-card__actions .el-button {
  flex: 1;
  min-height: var(--button-height-default);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Dialog Styles */
:deep(.el-dialog) {
  border-radius: var(--border-radius-lg);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border-light);
  padding: var(--spacing-lg) var(--spacing-xl);
}

:deep(.el-dialog__title) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-xl);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--color-border-light);
  padding: var(--spacing-lg) var(--spacing-xl);
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: row;
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .page-title {
    font-size: var(--font-size-h2);
  }

  .filter-card,
  .table-card {
    padding: var(--spacing-lg);
  }

  .filter-card :deep(.el-form-item) {
    width: 100%;
    margin-right: 0;
    margin-bottom: var(--spacing-md);
  }

  .filter-card :deep(.el-form-item:last-child) {
    margin-bottom: 0;
  }

  .filter-card :deep(.el-form-item__content) {
    width: 100%;
  }

  .org-card__actions {
    flex-direction: column;
  }

  .org-card__actions .el-button {
    width: 100%;
  }
}
</style>
