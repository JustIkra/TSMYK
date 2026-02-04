<template>
  <el-drawer
    :model-value="modelValue"
    :title="`Метрики участника: ${participantName}`"
    size="70%"
    direction="rtl"
    @update:model-value="handleClose"
  >
    <div
      v-loading="loading"
      class="metrics-drawer"
    >
      <!-- Refresh Button -->
      <div class="drawer-actions">
        <el-button
          type="primary"
          size="small"
          @click="loadMetrics"
        >
          <el-icon><Refresh /></el-icon>
          Обновить
        </el-button>
      </div>

      <!-- Metrics Table -->
      <el-table
        :data="metrics"
        stripe
        :empty-text="emptyText"
      >
        <el-table-column
          prop="metric_code"
          label="Код метрики"
          width="200"
        />
        <el-table-column
          label="Название метрики"
          min-width="250"
        >
          <template #default="{ row }">
            {{ getMetricName(row.metric_code) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="value"
          label="Значение"
          width="120"
        >
          <template #default="{ row }">
            <el-tag type="success">
              {{ formatFromApi(row.value) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="confidence"
          label="Уверенность"
          width="150"
        >
          <template #default="{ row }">
            <span
              v-if="row.confidence !== null"
              :style="{ color: getConfidenceColor(row.confidence) }"
            >
              {{ (row.confidence * 100).toFixed(0) }}%
            </span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="updated_at"
          label="Обновлено"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="last_source_report_id"
          label="Источник"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.last_source_report_id"
              size="small"
            >
              Из отчёта
            </el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- Empty State -->
      <el-empty
        v-if="!metrics.length && !loading"
        :description="emptyText"
      />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { participantsApi } from '@/api'
import { useMetricsStore } from '@/stores'
import { formatFromApi } from '@/utils/numberFormat'
import { getMetricDisplayName } from '@/utils/metricNames'
import { formatDate } from '@/utils/dateFormat'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  participantId: {
    type: String,
    required: true
  },
  participantName: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

// Store
const metricsStore = useMetricsStore()

// State
const loading = ref(false)
const metrics = ref([])

// Cached metric definitions from store
const metricDefs = computed(() => metricsStore.metricDefs)

// Computed
const emptyText = computed(() => {
  return 'Метрики ещё не извлечены. Загрузите и обработайте отчёты.'
})

// Methods
const handleClose = (value) => {
  emit('update:modelValue', value)
}

// Load metric definitions (uses cached store)
const loadMetricDefs = async () => {
  try {
    await metricsStore.fetchMetricDefs({ activeOnly: true })
  } catch (error) {
    console.error('Error loading metric definitions:', error)
  }
}

const loadMetrics = async () => {
  loading.value = true
  try {
    const response = await participantsApi.getMetrics(props.participantId)
    metrics.value = response.metrics || []
  } catch (error) {
    console.error('Error loading participant metrics:', error)
    ElMessage.error('Ошибка загрузки метрик участника')
  } finally {
    loading.value = false
  }
}

const getMetricName = (metricCode) => {
  if (!metricCode) return '—'
  const metricDef = metricDefs.value?.find(m => m.code === metricCode)

  // Suppress warnings in this component
  const logger = { warn: () => {} }

  return getMetricDisplayName(metricDef, metricCode, logger)
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return 'var(--el-color-success)'
  if (confidence >= 0.6) return 'var(--el-color-warning)'
  return 'var(--el-color-danger)'
}

// Watch for participantId changes
watch(() => props.participantId, async (newId) => {
  if (newId && props.modelValue) {
    await loadMetricDefs()
    await loadMetrics()
  }
})

// Watch for drawer opening
watch(() => props.modelValue, async (isOpen) => {
  if (isOpen && props.participantId) {
    await loadMetricDefs()
    await loadMetrics()
  }
})
</script>

<style scoped>
.metrics-drawer {
  padding: 0;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--spacing-lg);
  padding: 0 var(--spacing-lg);
}

:deep(.el-drawer) {
  --el-drawer-bg-color: var(--color-white);
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-drawer__title) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
}

:deep(.el-drawer__body) {
  padding: var(--spacing-xl);
  background-color: var(--color-white);
}

:deep(.el-table) {
  font-size: var(--font-size-base);
  border-radius: var(--border-radius-base);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  --el-table-border-color: var(--color-border-light);
  --el-table-header-bg-color: var(--color-gray-50);
  --el-table-row-hover-bg-color: var(--color-bg-hover);
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

:deep(.el-table .el-tag) {
  font-weight: var(--font-weight-medium);
  border-radius: var(--border-radius-sm);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background-color: var(--color-white-soft);
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

/* Confidence color classes */
.confidence-high {
  color: var(--color-success);
  font-weight: var(--font-weight-medium);
}

.confidence-medium {
  color: var(--color-warning);
  font-weight: var(--font-weight-medium);
}

.confidence-low {
  color: var(--color-danger);
  font-weight: var(--font-weight-medium);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .drawer-actions {
    padding: 0;
  }

  :deep(.el-drawer__body) {
    padding: var(--spacing-lg);
  }
}
</style>
