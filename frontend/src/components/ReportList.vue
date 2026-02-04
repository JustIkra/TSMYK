<template>
  <div class="report-list">
    <!-- Filters and Sort -->
    <div class="report-list__controls">
      <div class="controls-left">
        <el-select
          v-model="filterStatus"
          placeholder="Все статусы"
          clearable
          style="width: 200px"
          @change="handleFilterChange"
        >
          <el-option
            label="Все статусы"
            value=""
          />
          <el-option
            v-for="status in statusOptions"
            :key="status.value"
            :label="status.label"
            :value="status.value"
          />
        </el-select>
      </div>
      <div class="controls-right">
        <el-button
          :type="sortOrder === 'desc' ? 'primary' : 'default'"
          size="small"
          @click="toggleSort"
        >
          <el-icon><Sort /></el-icon>
          {{ sortOrder === 'desc' ? 'Новые сверху' : 'Старые сверху' }}
        </el-button>
      </div>
    </div>

    <!-- Desktop Table View -->
    <el-table
      v-if="!isMobile"
      v-loading="loading"
      :data="filteredAndSortedReports"
      class="report-list__table"
      stripe
      :empty-text="emptyText"
    >
      <el-table-column
        prop="file_ref.filename"
        label="Название файла"
        min-width="200"
      >
        <template #default="{ row }">
          <span class="filename">{{ row.file_ref?.filename || 'Без названия' }}</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="status"
        label="Статус"
        width="200"
      >
        <template #default="{ row }">
          <div class="status-cell">
            <el-icon
              v-if="row.status === 'PROCESSING'"
              class="status-icon status-icon--spinning"
            >
              <Loading />
            </el-icon>
            <el-icon
              v-else-if="row.status === 'EXTRACTED'"
              class="status-icon status-icon--success"
            >
              <CircleCheck />
            </el-icon>
            <el-icon
              v-else-if="row.status === 'FAILED'"
              class="status-icon status-icon--error"
            >
              <CircleClose />
            </el-icon>
            <el-icon
              v-else
              class="status-icon status-icon--info"
            >
              <Document />
            </el-icon>
            <el-tag
              :type="getStatusType(row.status)"
              size="default"
            >
              {{ formatStatus(row.status) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column
        prop="uploaded_at"
        label="Дата загрузки"
        width="180"
        sortable
      >
        <template #default="{ row }">
          {{ formatDate(row.uploaded_at) }}
        </template>
      </el-table-column>

      <el-table-column
        label="Действия"
        width="200"
        fixed="right"
        align="right"
      >
        <template #default="{ row }">
          <el-dropdown
            trigger="click"
            @command="handleAction"
          >
            <el-button
              type="primary"
              size="small"
            >
              Действия
              <el-icon class="el-icon--right">
                <ArrowDown />
              </el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <!-- Primary actions -->
                <el-dropdown-item
                  v-if="row.status === 'EXTRACTED'"
                  :command="{ action: 'edit', report: row }"
                >
                  <el-icon><Edit /></el-icon>
                  Редактировать метрики
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="row.status === 'PROCESSING' || row.status === 'EXTRACTED'"
                  :command="{ action: 'view', report: row }"
                >
                  <el-icon><View /></el-icon>
                  Просмотр метрик
                </el-dropdown-item>
                <el-dropdown-item
                  :command="{ action: 'extract', report: row }"
                >
                  <el-icon><DataAnalysis /></el-icon>
                  {{ row.status === 'FAILED' ? 'Повторить извлечение' : row.status === 'PROCESSING' ? 'Перезапустить извлечение' : row.status === 'EXTRACTED' ? 'Переизвлечь метрики' : 'Извлечь метрики' }}
                </el-dropdown-item>
                <el-dropdown-item
                  divided
                  :command="{ action: 'download', report: row }"
                >
                  <el-icon><Download /></el-icon>
                  Скачать
                </el-dropdown-item>
                <el-dropdown-item
                  :command="{ action: 'delete', report: row }"
                  class="dropdown-item--danger"
                >
                  <el-icon><Delete /></el-icon>
                  Удалить
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <!-- Mobile Card View -->
    <div
      v-else
      v-loading="loading"
      class="report-list__cards"
    >
      <el-card
        v-for="report in filteredAndSortedReports"
        :key="report.id"
        class="report-card"
        shadow="hover"
      >
        <template #header>
          <div class="report-card__header">
            <div class="report-card__status">
              <el-icon
                v-if="report.status === 'PROCESSING'"
                class="status-icon status-icon--spinning"
              >
                <Loading />
              </el-icon>
              <el-icon
                v-else-if="report.status === 'EXTRACTED'"
                class="status-icon status-icon--success"
              >
                <CircleCheck />
              </el-icon>
              <el-icon
                v-else-if="report.status === 'FAILED'"
                class="status-icon status-icon--error"
              >
                <CircleClose />
              </el-icon>
              <el-icon
                v-else
                class="status-icon status-icon--info"
              >
                <Document />
              </el-icon>
              <el-tag
                :type="getStatusType(report.status)"
                size="small"
              >
                {{ formatStatus(report.status) }}
              </el-tag>
            </div>
          </div>
        </template>

        <div class="report-card__body">
          <div class="report-card__field">
            <span class="field-label">Файл:</span>
            <span class="field-value field-value--filename">{{ report.file_ref?.filename || 'Без названия' }}</span>
          </div>
          <div class="report-card__field">
            <span class="field-label">Дата загрузки:</span>
            <span class="field-value">{{ formatDate(report.uploaded_at) }}</span>
          </div>
        </div>

        <template #footer>
          <div class="report-card__actions">
            <el-button
              v-if="report.status === 'EXTRACTED'"
              type="success"
              size="small"
              @click="handleAction({ action: 'edit', report })"
            >
              <el-icon><Edit /></el-icon>
              Редактировать
            </el-button>
            <el-button
              v-if="report.status === 'PROCESSING' || report.status === 'EXTRACTED'"
              type="info"
              size="small"
              @click="handleAction({ action: 'view', report })"
            >
              <el-icon><View /></el-icon>
              Просмотр
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="handleAction({ action: 'extract', report })"
            >
              <el-icon><DataAnalysis /></el-icon>
              {{ report.status === 'FAILED' ? 'Повторить' : report.status === 'PROCESSING' ? 'Перезапустить' : report.status === 'EXTRACTED' ? 'Переизвлечь' : 'Извлечь' }}
            </el-button>
            <el-button
              size="small"
              @click="handleAction({ action: 'download', report })"
            >
              <el-icon><Download /></el-icon>
              Скачать
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleAction({ action: 'delete', report })"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </template>
      </el-card>

      <el-empty
        v-if="!filteredAndSortedReports.length && !loading"
        :description="emptyText"
        :image-size="120"
      >
        <el-button
          v-if="!filterStatus"
          type="primary"
          @click="$emit('upload')"
        >
          Загрузить отчёт
        </el-button>
      </el-empty>
    </div>

    <!-- Empty State for Desktop -->
    <el-empty
      v-if="!filteredAndSortedReports.length && !loading && !isMobile"
      :description="emptyText"
      :image-size="120"
    >
      <el-button
        v-if="!filterStatus"
        type="primary"
        @click="$emit('upload')"
      >
        Загрузить отчёт
      </el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Sort,
  Loading,
  CircleCheck,
  CircleClose,
  Document,
  Edit,
  View,
  DataAnalysis,
  Download,
  Delete,
  ArrowDown
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { formatDate } from '@/utils/dateFormat'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps({
  reports: {
    type: Array,
    required: true,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'view',
  'edit',
  'extract',
  'download',
  'delete',
  'upload'
])

const route = useRoute()
const router = useRouter()

// Responsive
const { isMobile } = useResponsive()

onMounted(() => {
  // Load filters from URL
  if (route.query.status) {
    filterStatus.value = route.query.status
  }
  if (route.query.sort) {
    sortOrder.value = route.query.sort
  }
})

// Filters and Sort
const filterStatus = ref('')
const sortOrder = ref('desc') // 'desc' = newest first, 'asc' = oldest first

const statusOptions = [
  { label: 'Загружен', value: 'UPLOADED' },
  { label: 'Извлечение метрик...', value: 'PROCESSING' },
  { label: 'Метрики извлечены', value: 'EXTRACTED' },
  { label: 'Ошибка', value: 'FAILED' }
]

// Update URL when filters change
watch([filterStatus, sortOrder], ([status, sort]) => {
  const query = { ...route.query }
  if (status) {
    query.status = status
  } else {
    delete query.status
  }
  if (sort) {
    query.sort = sort
  } else {
    delete query.sort
  }
  router.replace({ query })
})

const handleFilterChange = () => {
  // URL update handled by watch
}

const toggleSort = () => {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

// Filtered and sorted reports
const filteredAndSortedReports = computed(() => {
  let result = [...props.reports]

  // Filter by status
  if (filterStatus.value) {
    result = result.filter(r => r.status === filterStatus.value)
  }

  // Sort by date
  result.sort((a, b) => {
    const dateA = new Date(a.uploaded_at)
    const dateB = new Date(b.uploaded_at)
    return sortOrder.value === 'desc' ? dateB - dateA : dateA - dateB
  })

  return result
})

const emptyText = computed(() => {
  if (filterStatus.value) {
    return 'Нет отчётов с выбранным статусом'
  }
  return 'Нет загруженных отчётов'
})

const formatStatus = (status) => {
  const statuses = {
    UPLOADED: 'Загружен',
    PROCESSING: 'Извлечение метрик...',
    EXTRACTED: 'Метрики извлечены',
    FAILED: 'Ошибка'
  }
  return statuses[status] || status
}

const getStatusType = (status) => {
  const types = {
    UPLOADED: 'info',
    PROCESSING: 'warning',
    EXTRACTED: 'success',
    FAILED: 'danger'
  }
  return types[status] || 'info'
}

// Actions
const handleAction = async ({ action, report }) => {
  switch (action) {
    case 'view':
      emit('view', report.id)
      break
    case 'edit':
      emit('edit', report.id)
      break
    case 'extract':
      emit('extract', report.id)
      break
    case 'download':
      emit('download', report.id)
      break
    case 'delete':
      try {
        await ElMessageBox.confirm(
          'Вы уверены, что хотите удалить этот отчёт?',
          'Подтверждение удаления',
          {
            confirmButtonText: 'Удалить',
            cancelButtonText: 'Отмена',
            type: 'warning'
          }
        )
        emit('delete', report.id)
      } catch {
        // User cancelled
      }
      break
  }
}
</script>

<style scoped>
.report-list {
  width: 100%;
}

.report-list__controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  gap: var(--spacing-lg);
  flex-wrap: wrap;
}

.controls-left,
.controls-right {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

/* Table Styles */
.report-list__table {
  width: 100%;
  border-radius: var(--border-radius-base);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

:deep(.el-table) {
  --el-table-border-color: var(--color-border-light);
  --el-table-header-bg-color: var(--color-gray-50);
  --el-table-row-hover-bg-color: var(--color-bg-hover);
  border-radius: var(--border-radius-base);
}

:deep(.el-table th) {
  background-color: var(--color-gray-50);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
}

:deep(.el-table td) {
  color: var(--color-text-regular);
  font-size: var(--font-size-base);
}

.filename {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  word-break: break-word;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.status-icon {
  font-size: 16px;
}

.status-icon--spinning {
  animation: rotate 1s linear infinite;
  color: var(--color-warning);
}

.status-icon--success {
  color: var(--color-success);
}

.status-icon--error {
  color: var(--color-danger);
}

.status-icon--info {
  color: var(--color-text-secondary);
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Card Styles (Mobile) */
.report-list__cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.report-card {
  width: 100%;
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  transition: var(--transition-fast);
}

.report-card:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--color-border);
}

:deep(.report-card .el-card__header) {
  background-color: var(--color-gray-50);
  border-bottom: 1px solid var(--color-border-light);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--border-radius-base) var(--border-radius-base) 0 0;
}

:deep(.report-card .el-card__body) {
  padding: var(--spacing-lg);
}

:deep(.report-card .el-card__footer) {
  background-color: var(--color-white);
  border-top: 1px solid var(--color-border-light);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: 0 0 var(--border-radius-base) var(--border-radius-base);
}

.report-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-card__status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.report-card__body {
  padding: var(--spacing-md) 0;
}

.report-card__field {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
  gap: var(--spacing-md);
}

.field-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}

.field-value {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  text-align: right;
  word-break: break-word;
  overflow-wrap: break-word;
}

.field-value--filename {
  max-width: 100%;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.report-card__actions {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.report-card__actions .el-button {
  width: 100%;
  min-height: 44px;
  margin: 0;
  border-radius: var(--border-radius-base);
}

/* Dropdown styling */
:deep(.el-dropdown-menu) {
  border-radius: var(--border-radius-base);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-xs);
}

:deep(.el-dropdown-menu__item) {
  color: var(--color-text-regular);
  transition: var(--transition-fast);
  border-radius: var(--border-radius-sm);
  padding: var(--spacing-sm) var(--spacing-md);
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: var(--color-bg-hover);
  color: var(--color-primary);
}

/* Dropdown danger item */
:deep(.dropdown-item--danger) {
  color: var(--color-danger);
}

:deep(.dropdown-item--danger:hover) {
  background-color: var(--color-danger-light);
  color: var(--color-danger);
}

/* Select styling */
:deep(.el-select .el-input__wrapper) {
  border-radius: var(--border-radius-base);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  transition: var(--transition-fast);
}

:deep(.el-select .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border-dark) inset;
}

:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-focus-ring);
}

/* Tag styling */
:deep(.el-tag) {
  border-radius: var(--border-radius-sm);
}

/* Empty state styling */
:deep(.el-empty) {
  padding: var(--spacing-3xl);
}

:deep(.el-empty__description) {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
}

/* Responsive */
@media (max-width: 768px) {
  .report-list__controls {
    flex-direction: column;
    align-items: stretch;
  }

  .controls-left,
  .controls-right {
    width: 100%;
  }

  .controls-left .el-select {
    width: 100%;
  }

  .controls-right .el-button {
    width: 100%;
  }
}

/* Extra small screens - vertical field layout */
@media (max-width: 375px) {
  .report-card__field {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
  }

  .field-value {
    text-align: left;
  }
}
</style>
