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

      <!-- Scoring Section -->
      <el-card class="section-card">
        <template #header>
          <div class="section-header">
            <h3>Скоринг по моделям компетенций</h3>
            <el-button
              type="primary"
              :loading="recalculatingScoring"
              @click="recalculateScoring"
            >
              <el-icon><Refresh /></el-icon>
              Пересчитать
            </el-button>
          </div>
        </template>

        <div
          v-loading="loadingScoring"
          class="scoring-content"
        >
          <el-empty
            v-if="!loadingScoring && scoringResults.length === 0"
            description="Скоринг ещё не рассчитан. Нажмите «Пересчитать» для расчёта."
          />

          <div
            v-else
            class="scoring-cards"
          >
            <el-card
              v-for="result in scoringResults"
              :key="result.id"
              class="scoring-result-card"
              shadow="hover"
            >
              <template #header>
                <div class="scoring-card-header">
                  <span class="scoring-model-name">{{ result.prof_activity_name }}</span>
                  <el-tag
                    :type="getScoreTagType(result.final_score)"
                    size="large"
                    class="scoring-final-tag"
                  >
                    {{ parseFloat(result.final_score).toFixed(1) }}
                  </el-tag>
                </div>
              </template>

              <div class="scoring-details">
                <div class="scoring-row">
                  <span class="scoring-label">Базовый балл:</span>
                  <span class="scoring-value">{{ parseFloat(result.base_score).toFixed(2) }}</span>
                </div>
                <div class="scoring-row">
                  <span class="scoring-label">Множитель штрафов:</span>
                  <span
                    class="scoring-value"
                    :class="{ 'scoring-value--penalty': parseFloat(result.penalty_multiplier) < 1 }"
                  >
                    × {{ parseFloat(result.penalty_multiplier).toFixed(2) }}
                  </span>
                </div>

                <el-divider
                  v-if="result.penalties_applied && result.penalties_applied.length > 0"
                />

                <div
                  v-if="result.penalties_applied && result.penalties_applied.length > 0"
                  class="scoring-penalties"
                >
                  <div class="penalties-header">
                    <el-icon color="var(--el-color-warning)"><Warning /></el-icon>
                    <span>Применённые штрафы:</span>
                  </div>
                  <div
                    v-for="(penalty, idx) in result.penalties_applied"
                    :key="idx"
                    class="penalty-item"
                  >
                    <span class="penalty-metric">{{ penalty.metric_code }}</span>
                    <span class="penalty-info">
                      {{ parseFloat(penalty.value).toFixed(1) }} &lt; {{ parseFloat(penalty.threshold).toFixed(1) }}
                    </span>
                    <el-tag
                      type="danger"
                      size="small"
                    >
                      -{{ (parseFloat(penalty.penalty) * 100).toFixed(0) }}%
                    </el-tag>
                  </div>
                </div>

                <el-text
                  v-else
                  type="success"
                  size="small"
                >
                  Штрафы не применены
                </el-text>
              </div>

              <div class="scoring-footer">
                <el-text
                  type="info"
                  size="small"
                >
                  Рассчитано: {{ formatDate(result.computed_at) }}
                </el-text>
              </div>
            </el-card>
          </div>
        </div>
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
          accept=".docx,.pdf"
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
              .docx и .pdf файлы, макс. 20 МБ, до 10 файлов
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
  CircleClose,
  Refresh,
  Warning
} from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import MetricsEditor from '@/components/MetricsEditor.vue'
import ReportList from '@/components/ReportList.vue'
import ParticipantMetricsDrawer from '@/components/ParticipantMetricsDrawer.vue'
import { useParticipantsStore, useMetricsStore } from '@/stores'
import { reportsApi, participantsApi } from '@/api'
import { scoringApi } from '@/api/scoring'
import { formatDate } from '@/utils/dateFormat'
import { useResponsive } from '@/composables/useResponsive'

const router = useRouter()
const route = useRoute()
const participantsStore = useParticipantsStore()
const metricsStore = useMetricsStore()

const loading = ref(false)
const loadingReports = ref(false)
const loadingScoring = ref(false)
const recalculatingScoring = ref(false)
const scoringResults = ref([])

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

const ALLOWED_EXTENSIONS = ['.docx', '.pdf']

const validateFile = (file) => {
  // Check extension
  const fileName = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext))) {
    return 'Только файлы формата .docx и .pdf'
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
    // Extract filename from Content-Disposition header or use default
    const contentDisposition = response.headers?.['content-disposition']
    let filename = `report_${reportId}`
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '')
      }
    }
    // Fallback: determine extension from content-type
    if (!filename.includes('.')) {
      const contentType = response.headers?.['content-type'] || ''
      const ext = contentType.includes('pdf') ? '.pdf' : '.docx'
      filename += ext
    }
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
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

// Scoring functions
const loadScoring = async () => {
  loadingScoring.value = true
  try {
    const data = await scoringApi.getParticipantScores(route.params.id)
    scoringResults.value = data.results || []
  } catch (error) {
    console.error('Error loading scoring:', error)
    // Don't show error message - scoring might not exist yet
    scoringResults.value = []
  } finally {
    loadingScoring.value = false
  }
}

const recalculateScoring = async () => {
  recalculatingScoring.value = true
  try {
    const results = await scoringApi.recalculateParticipant(route.params.id)
    scoringResults.value = results
    ElMessage.success(`Скоринг рассчитан для ${results.length} моделей`)
  } catch (error) {
    console.error('Error recalculating scoring:', error)
    ElMessage.error(error.response?.data?.detail || 'Ошибка расчёта скоринга')
  } finally {
    recalculatingScoring.value = false
  }
}

const getScoreTagType = (score) => {
  const value = parseFloat(score)
  if (value >= 7) return 'success'
  if (value >= 5) return 'warning'
  return 'danger'
}

onMounted(async () => {
  // Parallel loading of independent data sources (eliminates waterfall)
  await Promise.all([
    loadParticipant(),
    loadReports(),
    loadMetricDefs(),
    loadScoring()
  ])
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
/* ========================================
   PAGE CONTAINER
   ======================================== */
.participant-detail {
  max-width: var(--container-max-width);
  margin: 0 auto;
}

/* ========================================
   CARDS - Modern rounded design with soft shadows
   ======================================== */
.detail-card,
.section-card {
  margin-bottom: var(--spacing-xl);
  background-color: var(--color-bg-card);
  border: 1px solid var(--card-border-color);
  border-radius: var(--card-border-radius);
  box-shadow: var(--card-shadow);
  transition: var(--transition-base);
}

.detail-card:hover,
.section-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.detail-card :deep(.el-card__header),
.section-card :deep(.el-card__header) {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border-light);
  background-color: transparent;
}

.detail-card :deep(.el-card__body),
.section-card :deep(.el-card__body) {
  padding: var(--spacing-xl);
}

/* ========================================
   PAGE HEADER
   ======================================== */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-lg);
}

.card-header h2 {
  margin: 0;
  font-size: var(--font-size-h1);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

.header-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* ========================================
   SECTION HEADER
   ======================================== */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  font-size: var(--font-size-h2);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

/* ========================================
   REPORTS ACTIONS
   ======================================== */
.reports-actions-group {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-sm);
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.reports-actions-group .el-button {
  flex-shrink: 0;
}

/* ========================================
   DESCRIPTIONS - Info table styling
   ======================================== */
:deep(.el-descriptions) {
  --el-descriptions-item-bordered-label-background: var(--color-gray-50);
}

:deep(.el-descriptions__label) {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

:deep(.el-descriptions__content) {
  color: var(--color-text-primary);
}

:deep(.el-descriptions__body) {
  border-radius: var(--border-radius-base);
  overflow: hidden;
}

/* ========================================
   TABLE STYLING
   ======================================== */
.reports-table :deep(colgroup col) {
  width: 25% !important;
}

.reports-table :deep(.el-table__cell) {
  text-align: center;
}

/* ========================================
   BATCH UPLOAD
   ======================================== */
.batch-files-list {
  margin-top: var(--spacing-xl);
  max-height: 300px;
  overflow-y: auto;
  padding-right: var(--spacing-xs);
}

.batch-files-header {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-md);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.batch-file-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--border-radius-base);
  margin-bottom: var(--spacing-sm);
  background: var(--color-gray-50);
  border: 1px solid var(--color-border-lighter);
  transition: var(--transition-fast);
}

.batch-file-item:hover {
  background: var(--color-gray-100);
  border-color: var(--color-border-light);
}

.batch-file-item--success {
  background: var(--color-success-light);
  border-color: var(--color-success);
}

.batch-file-item--error {
  background: var(--color-danger-light);
  border-color: var(--color-danger);
}

.batch-file-icon {
  font-size: 20px;
  flex-shrink: 0;
  color: var(--color-gray-500);
}

.batch-file-icon--success {
  color: var(--color-success);
}

.batch-file-icon--error {
  color: var(--color-danger);
}

.batch-file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: var(--spacing-xs);
}

.batch-file-name {
  font-weight: var(--font-weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.batch-file-size {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.batch-file-error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
  font-weight: var(--font-weight-medium);
}

/* ========================================
   DIALOG STYLING - Modern rounded corners
   ======================================== */
:deep(.el-dialog) {
  border-radius: var(--border-radius-xl);
  box-shadow: var(--shadow-xl);
}

:deep(.el-dialog__header) {
  padding: var(--spacing-xl) var(--spacing-xl) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
}

:deep(.el-dialog__title) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-xl);
}

:deep(.el-dialog__footer) {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 1px solid var(--color-border-light);
}

/* ========================================
   UPLOAD STYLING
   ======================================== */
:deep(.el-upload-dragger) {
  border-radius: var(--border-radius-lg);
  border: 2px dashed var(--color-border);
  transition: var(--transition-fast);
  padding: var(--spacing-2xl) var(--spacing-xl);
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary);
  background-color: var(--color-primary-bg);
}

:deep(.el-upload__text) {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

:deep(.el-upload__text em) {
  color: var(--color-primary);
  font-style: normal;
  font-weight: var(--font-weight-medium);
}

:deep(.el-upload__tip) {
  color: var(--color-text-secondary);
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-xs);
}

:deep(.el-icon--upload) {
  font-size: 48px;
  color: var(--color-gray-400);
  margin-bottom: var(--spacing-md);
}

/* ========================================
   BUTTON STYLING - Non pill-shaped
   ======================================== */
:deep(.el-button) {
  border-radius: var(--button-border-radius);
}

/* ========================================
   TABS - Modern appearance
   ======================================== */
:deep(.el-tabs__header) {
  margin-bottom: var(--spacing-lg);
}

:deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: var(--color-border-light);
}

:deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  padding: 0 var(--spacing-lg);
  height: 44px;
  line-height: 44px;
  transition: var(--transition-fast);
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary);
}

:deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
  height: 2px;
  border-radius: 1px;
}

/* ========================================
   RESPONSIVE - Mobile
   ======================================== */
@media (max-width: 768px) {
  .detail-card :deep(.el-card__header),
  .detail-card :deep(.el-card__body),
  .section-card :deep(.el-card__header),
  .section-card :deep(.el-card__body) {
    padding: var(--spacing-lg);
  }

  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .card-header h2 {
    font-size: var(--font-size-h2);
  }

  .header-actions {
    flex-direction: column;
  }

  .header-actions .el-button {
    min-height: var(--button-height-large);
    width: 100%;
  }

  .section-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }

  .section-header .el-button {
    width: 100%;
    min-height: var(--button-height-large);
  }
}

/* ========================================
   RESPONSIVE - Small Mobile
   ======================================== */
@media (max-width: 375px) {
  .card-header h2 {
    font-size: var(--font-size-lg);
  }

  .section-header h3 {
    font-size: var(--font-size-lg);
  }
}

/* ========================================
   SCORING SECTION
   ======================================== */
.scoring-content {
  min-height: 100px;
}

.scoring-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-xl);
}

.scoring-result-card {
  border-radius: var(--border-radius-lg);
  transition: var(--transition-base);
}

.scoring-result-card:hover {
  transform: translateY(-2px);
}

.scoring-result-card :deep(.el-card__header) {
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-section);
  border-bottom: 1px solid var(--color-border-light);
}

.scoring-result-card :deep(.el-card__body) {
  padding: var(--spacing-lg);
}

.scoring-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scoring-model-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
}

.scoring-final-tag {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  padding: var(--spacing-sm) var(--spacing-md);
}

.scoring-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.scoring-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xs) 0;
}

.scoring-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.scoring-value {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.scoring-value--penalty {
  color: var(--color-warning);
}

.scoring-penalties {
  background: var(--color-warning-bg);
  border-radius: var(--border-radius-base);
  padding: var(--spacing-md);
}

.penalties-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-warning);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.penalty-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xs) 0;
  font-size: var(--font-size-sm);
}

.penalty-metric {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  flex: 1;
}

.penalty-info {
  color: var(--color-text-secondary);
}

.scoring-footer {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-lighter);
}

@media (max-width: 768px) {
  .scoring-cards {
    grid-template-columns: 1fr;
  }
}
</style>
