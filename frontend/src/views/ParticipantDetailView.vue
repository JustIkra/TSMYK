<template>
  <app-layout>
    <div
      v-loading="loading"
      class="participant-detail"
    >
      <!-- Participant Info Card -->
      <el-card
        v-if="participant"
        class="detail-card"
      >
        <template #header>
          <div class="card-header">
            <h2>{{ participant.full_name }}</h2>
            <div class="header-actions">
              <el-button @click="router.back()">
                Назад
              </el-button>
              <el-button
                type="info"
                @click="showMetricsDrawer = true"
              >
                <el-icon><DataLine /></el-icon>
                Метрики
              </el-button>
            </div>
          </div>
        </template>

        <el-descriptions
          :column="isMobile ? 1 : 2"
          border
        >
          <el-descriptions-item label="ФИО">
            {{ participant.full_name }}
          </el-descriptions-item>
          <el-descriptions-item label="Дата рождения">
            {{ participant.birth_date || 'Не указана' }}
          </el-descriptions-item>
          <el-descriptions-item label="Внешний ID">
            {{ participant.external_id || 'Не указан' }}
          </el-descriptions-item>
          <el-descriptions-item label="Дата создания">
            {{ formatDate(participant.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Reports Section -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3>Отчёты</h3>
            <el-button
              type="primary"
              @click="showUploadDialog = true"
            >
              <el-icon><Upload /></el-icon>
              Загрузить отчёт
            </el-button>
          </div>
        </template>

        <report-list
          :reports="reports"
          :loading="loadingReports"
          @view="viewMetrics"
          @edit="viewMetrics"
          @extract="extractMetrics"
          @download="downloadReport"
          @delete="handleDeleteReport"
          @upload="showUploadDialog = true"
        />
      </el-card>

      <!-- Upload Dialog -->
      <el-dialog
        v-model="showUploadDialog"
        title="Загрузить отчёты"
        :width="isMobile ? '95%' : '600px'"
        destroy-on-close
        @close="resetBatchUpload"
      >
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          multiple
          accept=".docx"
          :on-change="handleBatchFileChange"
          :show-file-list="false"
          drag
        >
          <el-icon class="el-icon--upload">
            <Upload />
          </el-icon>
          <div class="el-upload__text">
            Перетащите файлы сюда или <em>нажмите для выбора</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              Только .docx файлы, макс. 20 МБ, до 10 файлов
            </div>
          </template>
        </el-upload>

        <!-- Batch files list -->
        <div
          v-if="batchFiles.length"
          class="batch-files-list"
        >
          <div class="batch-files-header">
            Выбрано файлов: {{ batchFiles.length }}/{{ MAX_FILES_COUNT }}
          </div>
          <div
            v-for="item in batchFiles"
            :key="item.id"
            class="batch-file-item"
            :class="'batch-file-item--' + item.status"
          >
            <el-icon
              v-if="item.status === 'pending'"
              class="batch-file-icon"
            >
              <Document />
            </el-icon>
            <el-icon
              v-else-if="item.status === 'uploading'"
              class="batch-file-icon is-loading"
            >
              <Loading />
            </el-icon>
            <el-icon
              v-else-if="item.status === 'success'"
              class="batch-file-icon batch-file-icon--success"
            >
              <CircleCheck />
            </el-icon>
            <el-icon
              v-else-if="item.status === 'error'"
              class="batch-file-icon batch-file-icon--error"
            >
              <CircleClose />
            </el-icon>

            <div class="batch-file-info">
              <span class="batch-file-name">{{ item.name }}</span>
              <span class="batch-file-size">{{ formatFileSize(item.size) }}</span>
              <span
                v-if="item.error"
                class="batch-file-error"
              >{{ item.error }}</span>
            </div>

            <el-button
              v-if="item.status === 'pending' || item.status === 'error'"
              type="danger"
              :icon="Delete"
              circle
              size="small"
              @click="removeBatchFile(item.id)"
            />
          </div>
        </div>

        <template #footer>
          <el-button @click="showUploadDialog = false">
            Отмена
          </el-button>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!batchFiles.some(f => f.status === 'pending')"
            @click="uploadAllFiles"
          >
            Загрузить все ({{ batchFiles.filter(f => f.status === 'pending').length }})
          </el-button>
        </template>
      </el-dialog>

      <!-- Metrics Dialog -->
      <el-dialog
        v-model="showMetricsDialog"
        title="Метрики отчёта"
        width="90%"
        top="5vh"
        destroy-on-close
      >
        <MetricsEditor
          v-if="currentReportId"
          :report-id="currentReportId"
          :report-status="currentReportStatus"
          :report-extract-warning="currentReportExtractWarning"
          @metrics-updated="handleMetricsUpdated"
        />
      </el-dialog>

      <!-- Participant Metrics Drawer -->
      <ParticipantMetricsDrawer
        v-model="showMetricsDrawer"
        :participant-id="participant?.id"
        :participant-name="participant?.full_name"
      />
    </div>
  </app-layout>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Upload,
  Delete,
  DataLine,
  Document,
  Loading,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import MetricsEditor from '@/components/MetricsEditor.vue'
import ReportList from '@/components/ReportList.vue'
import ParticipantMetricsDrawer from '@/components/ParticipantMetricsDrawer.vue'
import { useParticipantsStore, useMetricsStore } from '@/stores'
import { reportsApi, participantsApi } from '@/api'
import { formatDate } from '@/utils/dateFormat'
import { useResponsive } from '@/composables/useResponsive'

const router = useRouter()
const route = useRoute()
const participantsStore = useParticipantsStore()
const metricsStore = useMetricsStore()

const loading = ref(false)
const loadingReports = ref(false)

// Mobile responsiveness
const { isMobile } = useResponsive()
const uploading = ref(false)

const participant = computed(() => participantsStore.currentParticipant)
const reports = ref([])
const currentReportId = ref(null)

// Use cached metric definitions from store
const metricDefs = computed(() => metricsStore.metricDefs)
const refreshInterval = ref(null)

// Check if any report is being processed
const hasProcessingReports = computed(() => {
  return reports.value.some(report => report.status === 'PROCESSING')
})

// Get status of the current report
const currentReportStatus = computed(() => {
  if (!currentReportId.value) return null
  const report = reports.value.find(r => r.id === currentReportId.value)
  return report?.status || null
})

// Get extract_warning of the current report
const currentReportExtractWarning = computed(() => {
  if (!currentReportId.value) return null
  const report = reports.value.find(r => r.id === currentReportId.value)
  return report?.extract_warning || null
})

const showUploadDialog = ref(false)
const showMetricsDialog = ref(false)
const showMetricsDrawer = ref(false)

const uploadRef = ref(null)
const fileList = ref([])

// Batch upload state
const batchFiles = ref([])
let fileIdCounter = 0

const loadParticipant = async () => {
  loading.value = true
  try {
    await participantsStore.getParticipant(route.params.id)
  } catch (error) {
    ElMessage.error('Участник не найден')
    router.push('/participants')
  } finally {
    loading.value = false
  }
}

const loadReports = async ({ silent = false } = {}) => {
  if (!silent) {
    loadingReports.value = true
  }
  try {
    const response = await participantsApi.getReports(route.params.id)
    reports.value = response.items || []
  } catch (error) {
    console.error('Error loading reports:', error)
    ElMessage.error('Ошибка загрузки списка отчётов')
  } finally {
    if (!silent) {
      loadingReports.value = false
    }
  }
}

// Load metric definitions (uses cached store)
const loadMetricDefs = async () => {
  try {
    await metricsStore.fetchMetricDefs({ activeOnly: true })
  } catch (error) {
    console.error('Error loading metric definitions:', error)
  }
}

// File upload - Batch support
const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB
const MAX_FILES_COUNT = 10

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const validateFile = (file) => {
  // Check extension
  if (!file.name.toLowerCase().endsWith('.docx')) {
    return 'Только файлы формата .docx'
  }
  // Check size
  if (file.size > MAX_FILE_SIZE) {
    return `Размер файла превышает ${formatFileSize(MAX_FILE_SIZE)}`
  }
  return null
}

const handleBatchFileChange = (uploadFile, _uploadFiles) => {
  const file = uploadFile.raw

  // Check total count
  if (batchFiles.value.length >= MAX_FILES_COUNT) {
    ElMessage.warning(`Максимальное количество файлов: ${MAX_FILES_COUNT}`)
    // Remove the file from el-upload's internal list
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
    return
  }

  // Validate file
  const error = validateFile(file)
  if (error) {
    ElMessage.error(error)
    // Remove the file from el-upload's internal list
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
    return
  }

  // Add to batch
  batchFiles.value.push({
    id: ++fileIdCounter,
    file: file,
    name: file.name,
    size: file.size,
    status: 'pending', // 'pending' | 'uploading' | 'success' | 'error'
    progress: 0,
    error: null,
    reportId: null
  })

  // Clear el-upload's file list to allow more selections
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const removeBatchFile = (id) => {
  batchFiles.value = batchFiles.value.filter(f => f.id !== id)
}

const uploadSingleFile = async (item) => {
  item.status = 'uploading'
  item.progress = 0
  try {
    const response = await reportsApi.upload(route.params.id, item.file)
    item.status = 'success'
    item.reportId = response.id
  } catch (err) {
    item.status = 'error'
    item.error = err.response?.data?.detail || 'Ошибка загрузки'
  }
}

const uploadAllFiles = async () => {
  const pending = batchFiles.value.filter(f => f.status === 'pending')

  if (pending.length === 0) {
    ElMessage.warning('Нет файлов для загрузки')
    return
  }

  uploading.value = true
  try {
    // Upload all files in parallel
    await Promise.allSettled(
      pending.map(item => uploadSingleFile(item))
    )

    // Show summary message
    const successCount = batchFiles.value.filter(f => f.status === 'success').length
    const errorCount = batchFiles.value.filter(f => f.status === 'error').length

    if (errorCount === 0) {
      ElMessage.success(`Загружено ${successCount} отчётов`)
      showUploadDialog.value = false
      resetBatchUpload()
    } else {
      ElMessage.warning(`Загружено: ${successCount}, ошибок: ${errorCount}`)
    }

    await loadReports()
  } finally {
    uploading.value = false
  }
}

const resetBatchUpload = () => {
  batchFiles.value = []
  fileList.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

const downloadReport = async (reportId) => {
  try {
    const response = await reportsApi.download(reportId)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${reportId}.docx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('Отчёт скачан')
  } catch (error) {
    ElMessage.error('Ошибка скачивания отчёта')
  }
}

const extractMetrics = async (reportId) => {
  try {
    await reportsApi.extract(reportId)
    ElMessage.success('Извлечение метрик запущено')
    // Немедленно обновим список отчетов
    await loadReports()
  } catch (error) {
    ElMessage.error('Ошибка запуска извлечения метрик')
  }
}

// Auto-refresh functions
const startAutoRefresh = () => {
  if (refreshInterval.value) return // Already running

  // Обновляем каждые 3 секунды
  refreshInterval.value = setInterval(async () => {
    try {
      await loadReports({ silent: true })
    } catch (error) {
      console.error('Auto-refresh error:', error)
    }
  }, 3000)
}

const stopAutoRefresh = () => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
}


// Watch for processing reports to enable/disable auto-refresh
watch(hasProcessingReports, (hasProcessing) => {
  if (hasProcessing) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})


const viewMetrics = async (reportId) => {
  currentReportId.value = reportId
  await nextTick() // Wait for DOM to update before opening dialog
  showMetricsDialog.value = true
}

const handleMetricsUpdated = async () => {
  ElMessage.success('Метрики обновлены')
  await loadReports({ silent: true })
}

const handleDeleteReport = async (reportId) => {
  try {
    await reportsApi.delete(reportId)
    ElMessage.success('Отчёт удалён')
    await loadReports()
  } catch (error) {
    ElMessage.error('Ошибка удаления отчёта')
  }
}

onMounted(async () => {
  // Parallel loading of independent data sources (eliminates waterfall)
  await Promise.all([
    loadParticipant(),
    loadReports(),
    loadMetricDefs()
  ])
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.participant-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.detail-card,
.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.card-header h2 {
  margin: 0;
  font-size: 24px;
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--color-text-primary);
}

.reports-actions-group {
  display: flex;
  flex-direction: row;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.reports-actions-group .el-button {
  flex-shrink: 0;
}

.reports-table :deep(colgroup col) {
  width: 25% !important;
}

.reports-table :deep(.el-table__cell) {
  text-align: center;
}

/* Batch upload styles */
.batch-files-list {
  margin-top: 20px;
  max-height: 300px;
  overflow-y: auto;
}

.batch-files-header {
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}

.batch-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 8px;
  background: var(--el-fill-color-light);
}

.batch-file-item--success {
  background: var(--el-color-success-light-9);
}

.batch-file-item--error {
  background: var(--el-color-danger-light-9);
}

.batch-file-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.batch-file-icon--success {
  color: var(--el-color-success);
}

.batch-file-icon--error {
  color: var(--el-color-danger);
}

.batch-file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.batch-file-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.batch-file-size {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.batch-file-error {
  font-size: 12px;
  color: var(--el-color-danger);
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .card-header h2 {
    font-size: 20px;
  }

  .header-actions {
    flex-direction: column;
  }

  .header-actions .el-button {
    min-height: 44px;
    width: 100%;
  }

  .section-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .section-header .el-button {
    width: 100%;
    min-height: 44px;
  }
}

@media (max-width: 375px) {
  .card-header h2 {
    font-size: 18px;
  }

  .section-header h3 {
    font-size: 16px;
  }
}
</style>
