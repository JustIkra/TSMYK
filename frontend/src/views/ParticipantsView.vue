<template>
  <app-layout>
    <div class="participants-view">
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">
            Участники
          </h1>
          <el-button
            type="primary"
            @click="showCreateDialog = true"
          >
            <el-icon><Plus /></el-icon>
            Добавить участника
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
              placeholder="Введите имя"
              clearable
              :style="isMobile ? 'width: 100%' : 'width: 300px'"
              @change="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="Внешний ID">
            <el-input
              v-model="searchForm.external_id"
              placeholder="Внешний ID"
              clearable
              :style="isMobile ? 'width: 100%' : 'width: 200px'"
              @change="handleSearch"
            />
          </el-form-item>
        </el-form>
      </div>

      <div
        v-loading="participantsStore.loading"
        class="table-card card"
      >
        <!-- Desktop Table View -->
        <el-table
          v-if="!isMobile"
          :data="participantsStore.participants"
          stripe
          table-layout="fixed"
        >
          <el-table-column
            prop="full_name"
            label="ФИО"
          />
          <el-table-column
            prop="birth_date"
            label="Дата рождения"
            width="150"
          />
          <el-table-column
            prop="external_id"
            label="Внешний ID"
            width="150"
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
                  @click="viewParticipant(row.id)"
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

        <!-- Mobile Card View -->
        <div
          v-else
          class="participants-cards"
        >
          <div
            v-for="participant in participantsStore.participants"
            :key="participant.id"
            class="participant-card"
          >
            <div class="participant-card__name">
              {{ participant.full_name }}
            </div>
            <div class="participant-card__info">
              <div class="participant-card__field">
                <span class="field-label">ID:</span>
                <span class="field-value">{{ participant.external_id || '—' }}</span>
              </div>
              <div class="participant-card__field">
                <span class="field-label">Дата рождения:</span>
                <span class="field-value">{{ participant.birth_date || '—' }}</span>
              </div>
            </div>
            <div class="participant-card__actions">
              <el-button
                type="primary"
                @click="viewParticipant(participant.id)"
              >
                Открыть
              </el-button>
              <el-button
                type="danger"
                plain
                @click="confirmDelete(participant)"
              >
                Удалить
              </el-button>
            </div>
          </div>

          <el-empty
            v-if="!participantsStore.participants.length && !participantsStore.loading"
            description="Нет участников"
            :image-size="120"
          >
            <el-button
              type="primary"
              @click="showCreateDialog = true"
            >
              Добавить участника
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
            :total="participantsStore.pagination.total"
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
            :total="participantsStore.pagination.total"
            :page-sizes="[10, 20, 50]"
            layout="prev, pager, next"
            small
            @current-change="handleSearch"
            @size-change="handleSearch"
          />
        </div>
      </div>

      <!-- Диалог создания -->
      <el-dialog
        v-model="showCreateDialog"
        title="Добавить участника"
        :width="isMobile ? '95%' : '500px'"
      >
        <el-form
          ref="createFormRef"
          :model="createForm"
          :rules="createRules"
          label-position="top"
        >
          <el-form-item
            label="ФИО"
            prop="full_name"
          >
            <el-input
              v-model="createForm.full_name"
              placeholder="Введите полное имя"
            />
          </el-form-item>
          <el-form-item
            label="Дата рождения"
            prop="birth_date"
          >
            <el-date-picker
              v-model="createForm.birth_date"
              type="date"
              placeholder="Выберите дату"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item
            label="Внешний ID"
            prop="external_id"
          >
            <el-input
              v-model="createForm.external_id"
              placeholder="Внешний идентификатор (необязательно)"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showCreateDialog = false">
            Отмена
          </el-button>
          <el-button
            type="primary"
            :loading="participantsStore.loading"
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
import { useParticipantsStore } from '@/stores'
import { useResponsive } from '@/composables/useResponsive'

const router = useRouter()
const participantsStore = useParticipantsStore()

// Responsive
const { isMobile } = useResponsive()

const searchForm = reactive({
  query: '',
  external_id: '',
  page: 1,
  size: 20
})

const showCreateDialog = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  full_name: '',
  birth_date: '',
  external_id: ''
})

const createRules = {
  full_name: [
    { required: true, message: 'Введите ФИО', trigger: 'blur' },
    { min: 1, max: 255, message: 'От 1 до 255 символов', trigger: 'blur' }
  ]
}

const handleSearch = async () => {
  try {
    await participantsStore.searchParticipants(searchForm)
  } catch (error) {
    ElMessage.error('Ошибка загрузки участников')
  }
}

const handleCreate = async () => {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await participantsStore.createParticipant(createForm)
      ElMessage.success('Участник создан')
      showCreateDialog.value = false
      createForm.full_name = ''
      createForm.birth_date = ''
      createForm.external_id = ''
      await handleSearch()
    } catch (error) {
      ElMessage.error(participantsStore.error || 'Ошибка создания участника')
    }
  })
}

const viewParticipant = (id) => {
  router.push(`/participants/${id}`)
}

const confirmDelete = (participant) => {
  ElMessageBox.confirm(
    `Вы уверены, что хотите удалить участника "${participant.full_name}"?`,
    'Подтверждение удаления',
    {
      confirmButtonText: 'Удалить',
      cancelButtonText: 'Отмена',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await participantsStore.deleteParticipant(participant.id)
      ElMessage.success('Участник удалён')
      await handleSearch()
    } catch (error) {
      ElMessage.error(participantsStore.error || 'Ошибка удаления участника')
    }
  }).catch(() => {})
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.participants-view {
  max-width: var(--container-max-width);
  margin: 0 auto;
}

/* Page Header */
.page-header {
  margin-bottom: var(--spacing-xl);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Filter Card */
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

/* Table Card */
.table-card {
  background-color: var(--color-bg-card);
}

/* Table Styles - Calm colors */
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

/* Actions Group */
.actions-group {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-sm);
  align-items: center;
}

.actions-group .el-button {
  margin: 0;
}

/* Pagination */
.pagination {
  margin-top: var(--spacing-xl);
  display: flex;
  justify-content: flex-end;
}

.pagination--mobile {
  justify-content: center;
}

/* Mobile Card Styles */
.participants-cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.participant-card {
  width: 100%;
  background-color: var(--color-bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-lg);
  transition: var(--transition-base);
}

.participant-card:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--color-border);
}

.participant-card__name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.participant-card__info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
}

.participant-card__field {
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

.participant-card__actions {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-sm);
}

.participant-card__actions .el-button {
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

/* Responsive */
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

  .participant-card__actions {
    flex-direction: column;
  }

  .participant-card__actions .el-button {
    width: 100%;
  }
}
</style>
