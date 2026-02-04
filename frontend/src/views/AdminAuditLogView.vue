<template>
  <app-layout>
    <div class="audit-log-view">
      <el-card class="header-card">
        <div class="header-content">
          <div>
            <h1>Журнал аудита</h1>
            <p>История операций с метриками</p>
          </div>
        </div>
      </el-card>

      <!-- Фильтры -->
      <el-card class="filters-card">
        <el-form
          :inline="true"
          :model="filters"
          class="filters-form"
        >
          <el-form-item label="Период">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="—"
              start-placeholder="Начало"
              end-placeholder="Конец"
              format="DD.MM.YYYY"
              value-format="YYYY-MM-DDTHH:mm:ss"
              :shortcuts="dateShortcuts"
              @change="handleDateChange"
            />
          </el-form-item>

          <el-form-item label="Действие">
            <el-select
              v-model="filters.action"
              placeholder="Все действия"
              clearable
              style="width: 200px"
              @change="loadAuditLog"
            >
              <el-option
                v-for="action in actionTypes"
                :key="action"
                :label="getActionLabel(action)"
                :value="action"
              />
            </el-select>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              @click="loadAuditLog"
            >
              <el-icon><Search /></el-icon>
              Применить
            </el-button>
            <el-button @click="resetFilters">
              Сбросить
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Таблица -->
      <el-card
        v-loading="loading"
        class="table-card"
      >
        <el-table
          v-if="auditLogs.length > 0"
          :data="auditLogs"
          stripe
          style="width: 100%"
          table-layout="fixed"
        >
          <el-table-column
            label="Дата и время"
            width="180"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.timestamp) }}
            </template>
          </el-table-column>

          <el-table-column
            label="Пользователь"
            width="200"
          >
            <template #default="{ row }">
              <div v-if="row.user">
                <div class="user-name">
                  {{ row.user.full_name || row.user.email }}
                </div>
                <div
                  v-if="row.user.full_name"
                  class="user-email"
                >
                  {{ row.user.email }}
                </div>
              </div>
              <span
                v-else
                class="text-muted"
              >Система</span>
            </template>
          </el-table-column>

          <el-table-column
            label="Действие"
            width="150"
          >
            <template #default="{ row }">
              <el-tag :type="getActionTagType(row.action)">
                {{ getActionLabel(row.action) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column
            label="Коды метрик"
          >
            <template #default="{ row }">
              <div class="metric-codes">
                <el-tag
                  v-for="code in row.metric_codes.slice(0, 5)"
                  :key="code"
                  size="small"
                  type="info"
                  class="metric-code-tag"
                >
                  {{ code }}
                </el-tag>
                <el-tag
                  v-if="row.metric_codes.length > 5"
                  size="small"
                  type="info"
                >
                  +{{ row.metric_codes.length - 5 }}
                </el-tag>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            label="Затронуто"
            width="200"
          >
            <template #default="{ row }">
              <div
                v-if="row.affected_counts"
                class="affected-counts"
              >
                <div v-if="row.affected_counts.extracted_metrics">
                  Извлеч. метрик: {{ row.affected_counts.extracted_metrics }}
                </div>
                <div v-if="row.affected_counts.synonyms">
                  Синонимов: {{ row.affected_counts.synonyms }}
                </div>
                <div v-if="row.affected_counts.weight_tables">
                  Весовых таблиц: {{ row.affected_counts.weight_tables }}
                </div>
              </div>
              <span
                v-else
                class="text-muted"
              >—</span>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-else-if="!loading"
          description="Нет записей"
        />

        <!-- Пагинация -->
        <div
          v-if="total > 0"
          class="pagination-wrapper"
        >
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>
  </app-layout>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { adminApi } from '@/api/admin'

// State
const loading = ref(false)
const auditLogs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const actionTypes = ref([])

// Filters
const dateRange = ref(null)
const filters = ref({
  start_date: null,
  end_date: null,
  action: null
})

// Date shortcuts
const dateShortcuts = [
  {
    text: 'Сегодня',
    value: () => {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const end = new Date()
      end.setHours(23, 59, 59, 999)
      return [today, end]
    }
  },
  {
    text: 'Последние 7 дней',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      return [start, end]
    }
  },
  {
    text: 'Последние 30 дней',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      return [start, end]
    }
  }
]

// Action labels
const actionLabels = {
  bulk_delete: 'Массовое удаление',
  delete: 'Удаление',
  create: 'Создание',
  update: 'Обновление'
}

const getActionLabel = (action) => {
  return actionLabels[action] || action
}

const getActionTagType = (action) => {
  const types = {
    bulk_delete: 'danger',
    delete: 'danger',
    create: 'success',
    update: 'warning'
  }
  return types[action] || 'info'
}

// Date formatting
const formatDateTime = (timestamp) => {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Handlers
const handleDateChange = (range) => {
  if (range && range.length === 2) {
    filters.value.start_date = range[0]
    filters.value.end_date = range[1]
  } else {
    filters.value.start_date = null
    filters.value.end_date = null
  }
  loadAuditLog()
}

const handleSizeChange = () => {
  currentPage.value = 1
  loadAuditLog()
}

const handlePageChange = () => {
  loadAuditLog()
}

const resetFilters = () => {
  dateRange.value = null
  filters.value = {
    start_date: null,
    end_date: null,
    action: null
  }
  currentPage.value = 1
  loadAuditLog()
}

// API calls
const loadAuditLog = async () => {
  loading.value = true
  try {
    const params = {
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value
    }

    if (filters.value.start_date) {
      params.start_date = filters.value.start_date
    }
    if (filters.value.end_date) {
      params.end_date = filters.value.end_date
    }
    if (filters.value.action) {
      params.action = filters.value.action
    }

    const response = await adminApi.getAuditLog(params)
    auditLogs.value = response.items || []
    total.value = response.total || 0
  } catch (err) {
    console.error('Failed to load audit log:', err)
    ElMessage.error('Не удалось загрузить журнал аудита')
  } finally {
    loading.value = false
  }
}

const loadActionTypes = async () => {
  try {
    const response = await adminApi.getAuditActionTypes()
    actionTypes.value = response.actions || []
  } catch (err) {
    console.error('Failed to load action types:', err)
  }
}

// Init
onMounted(async () => {
  await Promise.all([
    loadAuditLog(),
    loadActionTypes()
  ])
})
</script>

<style scoped>
.audit-log-view {
  max-width: var(--container-max-width);
  margin: 0 auto;
}

/* Header Card */
.header-card {
  margin-bottom: var(--spacing-2xl);
}

.header-card :deep(.el-card__body) {
  padding: var(--spacing-xl);
}

.header-content h1 {
  font-size: var(--font-size-h1);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.header-content p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

/* Filters Card */
.filters-card {
  margin-bottom: var(--spacing-2xl);
}

.filters-card :deep(.el-card__body) {
  padding: var(--spacing-lg) var(--spacing-xl);
}

.filters-form {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
  align-items: flex-end;
}

.filters-form :deep(.el-form-item) {
  margin-bottom: 0;
}

/* Table Card */
.table-card {
  /* Uses default el-card styling from theme-tokens */
}

.table-card :deep(.el-card__body) {
  padding: var(--spacing-xl);
}

/* User info */
.user-name {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.user-email {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.text-muted {
  color: var(--color-text-placeholder);
  font-size: var(--font-size-sm);
}

/* Metric codes */
.metric-codes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
}

.metric-code-tag {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace;
  font-size: var(--font-size-xs);
}

/* Affected counts */
.affected-counts {
  font-size: var(--font-size-xs);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-regular);
}

.affected-counts div {
  margin-bottom: 2px;
}

.affected-counts div:last-child {
  margin-bottom: 0;
}

/* Pagination */
.pagination-wrapper {
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
  display: flex;
  justify-content: flex-end;
}

/* Table styling */
:deep(.el-table) {
  --el-table-border-color: var(--color-border-light);
  border-radius: var(--border-radius-lg);
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-bg-section);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid var(--color-border-lighter);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background-color: var(--color-white-soft);
}

/* Form styling */
:deep(.el-form-item__label) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
}

/* Empty state */
:deep(.el-empty) {
  padding: var(--spacing-2xl) 0;
}

:deep(.el-empty__description) {
  color: var(--color-text-secondary);
}

/* Date picker styling */
:deep(.el-date-editor) {
  --el-date-editor-width: auto;
}

:deep(.el-date-editor .el-input__wrapper) {
  border-radius: var(--border-radius-base);
}

/* Select styling */
:deep(.el-select .el-input__wrapper) {
  border-radius: var(--border-radius-base);
}

/* Pagination styling */
:deep(.el-pagination) {
  font-weight: var(--font-weight-normal);
  font-size: var(--font-size-sm);
}

:deep(.el-pagination .el-pager li) {
  border-radius: var(--border-radius-sm);
}

:deep(.el-pagination .el-pager li.is-active) {
  background-color: var(--color-primary);
  color: var(--color-white);
}

:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next) {
  border-radius: var(--border-radius-sm);
}

/* Responsive */
@media (max-width: 768px) {
  .filters-form {
    flex-direction: column;
    align-items: stretch;
  }

  .filters-form :deep(.el-form-item) {
    width: 100%;
  }

  .filters-form :deep(.el-select),
  .filters-form :deep(.el-date-editor) {
    width: 100% !important;
  }

  .pagination-wrapper {
    justify-content: center;
  }
}
</style>
