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
import { participantsApi, metricsApi } from '@/api'
import { formatFromApi } from '@/utils/numberFormat'
import { getMetricDisplayName } from '@/utils/metricNames'

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

// State
const loading = ref(false)
const metrics = ref([])
const metricDefs = ref([])

// Computed
const emptyText = computed(() => {
  return 'Метрики ещё не извлечены. Загрузите и обработайте отчёты.'
})

// Methods
const handleClose = (value) => {
  emit('update:modelValue', value)
}

const loadMetricDefs = async () => {
  try {
    const response = await metricsApi.listMetricDefs(true) // activeOnly = true
    metricDefs.value = response.items || []
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
  const metricDef = metricDefs.value.find(m => m.code === metricCode)

  // Suppress warnings in this component
  const logger = { warn: () => {} }

  return getMetricDisplayName(metricDef, metricCode, logger)
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return 'var(--el-color-success)'
  if (confidence >= 0.6) return 'var(--el-color-warning)'
  return 'var(--el-color-danger)'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  const parsedDate = new Date(dateStr)
  if (Number.isNaN(parsedDate.getTime())) return '—'
  return parsedDate.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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
  margin-bottom: 16px;
  padding: 0 20px;
}

:deep(.el-drawer__header) {
  margin-bottom: 20px;
  padding: 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

:deep(.el-drawer__body) {
  padding: 20px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table .el-tag) {
  font-weight: 500;
}
</style>
