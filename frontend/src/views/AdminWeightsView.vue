<template>
  <app-layout>
    <div class="admin-weights-view">
      <el-card class="header-card">
        <div class="header-content">
          <div>
            <h1>Управление весовыми таблицами</h1>
            <p>Каждая профессиональная область имеет свою уникальную весовую таблицу</p>
          </div>
          <div class="header-buttons">
            <el-button
              size="large"
              type="primary"
              @click="showProfActivityDialog"
            >
              <el-icon><FolderAdd /></el-icon>
              Новая область
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- Поиск по названию области -->
      <el-card class="search-card">
        <el-input
          v-model="searchQuery"
          placeholder="Поиск по названию профессиональной области..."
          :prefix-icon="Search"
          size="large"
          clearable
        />
      </el-card>

      <!-- Группировка по профессиональным областям -->
      <div
        v-loading="loading"
        class="areas-container"
      >
        <!-- Error State -->
        <el-result
          v-if="error"
          icon="error"
          title="Ошибка загрузки"
          :sub-title="error"
        >
          <template #extra>
            <el-button
              type="primary"
              @click="loadData"
            >
              <el-icon><RefreshRight /></el-icon>
              Повторить
            </el-button>
          </template>
        </el-result>

        <!-- Empty State -->
        <el-empty
          v-else-if="filteredAreas.length === 0 && !loading"
          description="Нет профессиональных областей"
        >
          <el-button
            type="primary"
            @click="showProfActivityDialog"
          >
            <el-icon><FolderAdd /></el-icon>
            Создать первую область
          </el-button>
        </el-empty>

        <!-- Data Grid -->
        <div
          v-else
          class="areas-grid"
        >
          <div
            v-for="area in filteredAreas"
            :key="area.id"
            class="area-card-wrapper"
          >
            <el-card
              class="area-card"
              shadow="hover"
            >
              <template #header>
                <div class="area-header">
                  <div class="area-title">
                    <el-icon
                      :size="24"
                      class="icon-primary"
                    >
                      <Folder />
                    </el-icon>
                    <h3>{{ area.name }}</h3>
                  </div>
                  <el-button
                    size="small"
                    circle
                    @click="editProfActivity(area)"
                  >
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </div>
                <div
                  v-if="area.description"
                  class="area-description"
                >
                  {{ area.description }}
                </div>
              </template>

              <!-- Весовая таблица области -->
              <div
                v-if="!area.weightTable"
                class="no-table"
              >
                <el-empty
                  description="Весовая таблица не создана"
                  :image-size="80"
                >
                  <el-button
                    type="primary"
                    @click="createTableForArea(area)"
                  >
                    <el-icon><Plus /></el-icon>
                    Создать таблицу
                  </el-button>
                </el-empty>
              </div>

              <div
                v-else
                class="table-info"
              >
                <div class="table-stats">
                  <div class="stat-item">
                    <span class="stat-label">Компетенций:</span>
                    <el-tag size="large">
                      {{ area.weightTable.weights.length }}
                    </el-tag>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Сумма весов:</span>
                    <el-tag
                      :type="getWeightSumType(area.weightTable)"
                      size="large"
                    >
                      {{ calculateWeightSum(area.weightTable).toFixed(4) }}
                    </el-tag>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Обновлена:</span>
                    <el-text type="info">
                      {{ formatDate(area.weightTable.created_at) }}
                    </el-text>
                  </div>
                </div>

                <div class="table-actions">
                  <el-button
                    type="info"
                    @click="viewDetails(area.weightTable)"
                  >
                    <el-icon><View /></el-icon>
                    Просмотр
                  </el-button>
                  <el-button
                    type="primary"
                    @click="editTable(area.weightTable)"
                  >
                    <el-icon><Edit /></el-icon>
                    Редактировать
                  </el-button>
                </div>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </div>

    <!-- Диалог создания/редактирования весовой таблицы -->
    <el-dialog
      v-model="tableDialogVisible"
      :title="dialogTitle"
      width="1100px"
      :close-on-click-modal="false"
      align-center
      class="weights-dialog"
    >
      <el-form
        ref="formRef"
        :model="tableForm"
        label-width="200px"
        label-position="top"
      >
        <!-- Профессиональная область -->
        <el-form-item
          label="Профессиональная область"
          :required="!editingTable"
        >
          <el-card
            shadow="never"
            class="area-display-card"
          >
            <div class="selected-area">
              <el-icon
                :size="20"
                class="icon-primary"
              >
                <Folder />
              </el-icon>
              <span class="area-name">{{ selectedActivityName }}</span>
            </div>
          </el-card>
        </el-form-item>

        <el-divider content-position="left">
          Компетенции и веса
        </el-divider>

        <!-- Индикатор суммы весов - компактный прогресс-бар сверху -->
        <div class="weight-sum-indicator">
          <div class="weight-sum-header">
            <span class="weight-sum-label">Сумма весов:</span>
            <span class="weight-sum-value">{{ currentWeightSum.toFixed(2) }} / 1.00</span>
            <span
              v-if="Math.abs(currentWeightSum - 1.0) >= 0.0001"
              class="weight-sum-remaining"
              :class="{ 'is-over': currentWeightSum > 1.0 }"
            >
              <template v-if="currentWeightSum < 1.0">
                Осталось: {{ (1.0 - currentWeightSum).toFixed(2) }}
              </template>
              <template v-else>
                Превышение: {{ (currentWeightSum - 1.0).toFixed(2) }}
              </template>
            </span>
          </div>
          <el-progress
            :percentage="Math.min(currentWeightSum * 100, 100)"
            :stroke-width="8"
            :show-text="false"
            :status="weightSumProgressStatus"
          />
        </div>

        <!-- Двухколоночный редактор -->
        <div class="weights-editor-grid">
          <!-- Левая колонка - Список компетенций -->
          <div class="competency-list">
            <div class="competency-list-header">
              <span>Компетенции ({{ tableForm.weights.length }})</span>
            </div>
            <div class="competency-list-items">
              <div
                v-for="(weight, index) in tableForm.weights"
                :key="index"
                class="competency-list-item"
                :class="{ 'is-selected': selectedWeightIndex === index }"
                @click="selectWeight(index)"
              >
                <div class="competency-item-header">
                  <span
                    v-if="weight.is_critical"
                    class="critical-icon"
                    title="Критическая компетенция"
                  >
                    <el-icon color="var(--color-danger)"><Warning /></el-icon>
                  </span>
                  <span class="competency-name">{{ getWeightDisplayName(weight) }}</span>
                  <span class="competency-weight">{{ (parseFloat(weight.weight) || 0).toFixed(2) }}</span>
                  <span class="competency-percent">({{ ((parseFloat(weight.weight) || 0) * 100).toFixed(0) }}%)</span>
                </div>
                <el-progress
                  :percentage="(parseFloat(weight.weight) || 0) * 100"
                  :stroke-width="4"
                  :show-text="false"
                  :color="weight.is_critical ? 'var(--color-danger)' : 'var(--color-primary)'"
                />
              </div>
              <div
                v-if="tableForm.weights.length === 0"
                class="competency-list-empty"
              >
                <el-text type="info">
                  Нет компетенций
                </el-text>
              </div>
            </div>
            <el-button
              type="primary"
              plain
              :icon="Plus"
              class="add-competency-btn"
              @click="addWeight"
            >
              Добавить компетенцию
            </el-button>
          </div>

          <!-- Правая колонка - Панель деталей -->
          <div class="competency-detail">
            <template v-if="selectedWeightIndex !== null && tableForm.weights[selectedWeightIndex]">
              <div class="detail-header">
                <h4 class="detail-title">{{ getWeightDisplayName(tableForm.weights[selectedWeightIndex]) || 'Новая компетенция' }}</h4>
                <el-button
                  type="danger"
                  :icon="Delete"
                  circle
                  size="small"
                  @click="removeWeight(selectedWeightIndex)"
                />
              </div>

              <!-- Секция: Выбор компетенции -->
              <div class="detail-section">
                <label class="detail-label">Компетенция</label>
                <el-select
                  v-model="tableForm.weights[selectedWeightIndex].metric_code"
                  placeholder="Поиск метрики..."
                  filterable
                  class="detail-select"
                >
                  <el-option
                    v-for="metric in availableMetrics"
                    :key="metric.code"
                    :label="`${resolveMetricName(metric)} (${metric.code})`"
                    :value="metric.code"
                  />
                </el-select>
                <div
                  v-if="tableForm.weights[selectedWeightIndex].metric_code"
                  class="metric-code-hint"
                >
                  Код: {{ tableForm.weights[selectedWeightIndex].metric_code }}
                </div>
              </div>

              <!-- Секция: Вес -->
              <div class="detail-section">
                <div class="detail-label-row">
                  <label class="detail-label">Вес</label>
                  <el-input-number
                    v-model="tableForm.weights[selectedWeightIndex].weight"
                    :min="0"
                    :max="1"
                    :step="0.01"
                    :precision="2"
                    size="small"
                    class="weight-input"
                  />
                </div>
                <el-slider
                  v-model="tableForm.weights[selectedWeightIndex].weight"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  :show-tooltip="false"
                />
                <div class="weight-actions">
                  <span class="remaining-hint">Осталось распределить: {{ remainingWeight.toFixed(2) }}</span>
                  <el-button
                    v-if="remainingWeight > 0"
                    type="primary"
                    size="small"
                    text
                    @click="fillRemainingWeight"
                  >
                    Заполнить остаток
                  </el-button>
                </div>
              </div>

              <!-- Секция: Критичность -->
              <div class="detail-section">
                <div class="critical-toggle">
                  <div class="critical-toggle-label">
                    <el-icon color="var(--color-danger)"><Warning /></el-icon>
                    <span>Критичность</span>
                  </div>
                  <el-switch
                    v-model="tableForm.weights[selectedWeightIndex].is_critical"
                    @change="onCriticalChange(tableForm.weights[selectedWeightIndex])"
                  />
                </div>

                <!-- Параметры критичности -->
                <div
                  v-if="tableForm.weights[selectedWeightIndex].is_critical"
                  class="critical-params"
                >
                  <!-- Штраф -->
                  <div class="critical-param">
                    <div class="detail-label-row">
                      <label class="detail-label">Штраф за невыполнение</label>
                      <el-input-number
                        v-model="tableForm.weights[selectedWeightIndex].penalty"
                        :min="0"
                        :max="0.99"
                        :step="0.05"
                        :precision="2"
                        size="small"
                        class="penalty-input"
                      />
                    </div>
                    <el-slider
                      v-model="tableForm.weights[selectedWeightIndex].penalty"
                      :min="0"
                      :max="0.99"
                      :step="0.01"
                      :show-tooltip="false"
                    />
                  </div>

                  <!-- Порог -->
                  <div class="critical-param">
                    <div class="detail-label-row">
                      <label class="detail-label">Минимальный порог</label>
                      <div class="threshold-value">
                        <el-input-number
                          v-model="tableForm.weights[selectedWeightIndex].threshold"
                          :min="1"
                          :max="10"
                          :step="0.5"
                          :precision="1"
                          size="small"
                          class="threshold-input"
                        />
                        <span class="threshold-unit">балл.</span>
                      </div>
                    </div>
                    <el-slider
                      v-model="tableForm.weights[selectedWeightIndex].threshold"
                      :min="1"
                      :max="10"
                      :step="0.5"
                      :show-tooltip="false"
                    />
                  </div>

                  <div class="critical-hint">
                    <el-icon><InfoFilled /></el-icon>
                    <span>Штраф применяется, если оценка ниже порога</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- Пустое состояние -->
            <div
              v-else
              class="detail-empty"
            >
              <el-icon
                :size="48"
                color="var(--color-gray-400)"
              >
                <Select />
              </el-icon>
              <p>Выберите компетенцию для редактирования</p>
              <p class="detail-empty-hint">
                или добавьте новую
              </p>
            </div>
          </div>
        </div>

        <el-divider />

        <el-form-item label="Метаданные (опционально)">
          <el-input
            v-model="tableForm.metadata.description"
            type="textarea"
            :rows="3"
            placeholder="Описание версии таблицы, примечания и т.д."
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="tableDialogVisible = false">
          Отмена
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!isValidWeightSum"
          @click="saveTable"
        >
          {{ editingTable ? 'Сохранить' : 'Создать' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Диалог просмотра весовой таблицы -->
    <el-dialog
      v-model="detailsDialogVisible"
      :title="`Весовая таблица: ${selectedTable?.prof_activity_name}`"
      width="900px"
      align-center
    >
      <div v-if="selectedTable">
        <el-card
          shadow="never"
          class="table-summary-card"
        >
          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item
              label="Профессиональная область"
              :span="2"
            >
              {{ selectedTable.prof_activity_name }}
            </el-descriptions-item>
            <el-descriptions-item label="Создана">
              {{ formatDate(selectedTable.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="Сумма весов">
              <el-tag
                :type="getWeightSumType(selectedTable)"
                size="large"
              >
                {{ calculateWeightSum(selectedTable).toFixed(4) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-divider content-position="left">
          <el-icon><View /></el-icon>
          Компетенции ({{ selectedTable.weights.length }})
        </el-divider>

        <el-table
          :data="enrichedWeights(selectedTable.weights)"
          stripe
          max-height="500"
          size="large"
          table-layout="fixed"
        >
          <el-table-column
            type="index"
            label="#"
            width="50"
            align="center"
          />
          <el-table-column
            label="Метрика"
            min-width="200"
          >
            <template #default="{ row }">
              <div class="metric-cell">
                <strong>{{ row.metric_name }}</strong>
                <br>
                <el-text
                  size="small"
                  type="info"
                >
                  {{ row.metric_code }}
                </el-text>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="weight"
            label="Вес"
            width="100"
            align="center"
          >
            <template #default="{ row }">
              <el-tag size="large">
                {{ parseFloat(row.weight).toFixed(2) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="%"
            width="80"
            align="center"
          >
            <template #default="{ row }">
              <el-text type="info">
                {{ (parseFloat(row.weight) * 100).toFixed(0) }}%
              </el-text>
            </template>
          </el-table-column>
          <el-table-column
            label="Критическая"
            width="110"
            align="center"
          >
            <template #default="{ row }">
              <el-tag
                v-if="row.is_critical"
                type="danger"
                size="small"
              >
                Да
              </el-tag>
              <el-text
                v-else
                type="info"
                size="small"
              >
                —
              </el-text>
            </template>
          </el-table-column>
          <el-table-column
            label="Штраф"
            width="90"
            align="center"
          >
            <template #default="{ row }">
              <el-tag
                v-if="row.is_critical && parseFloat(row.penalty) > 0"
                type="warning"
                size="small"
              >
                {{ parseFloat(row.penalty).toFixed(2) }}
              </el-tag>
              <el-text
                v-else
                type="info"
                size="small"
              >
                —
              </el-text>
            </template>
          </el-table-column>
          <el-table-column
            label="Порог"
            width="80"
            align="center"
          >
            <template #default="{ row }">
              <el-text
                v-if="row.is_critical"
                size="small"
              >
                &lt; {{ parseFloat(row.threshold).toFixed(1) }}
              </el-text>
              <el-text
                v-else
                type="info"
                size="small"
              >
                —
              </el-text>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="selectedTable.metadata && selectedTable.metadata.description"
          style="margin-top: 20px"
        >
          <el-divider content-position="left">
            Описание
          </el-divider>
          <el-card
            shadow="never"
            class="metadata-card"
          >
            {{ selectedTable.metadata.description }}
          </el-card>
        </div>
      </div>

      <template #footer>
        <el-button
          size="large"
          @click="detailsDialogVisible = false"
        >
          Закрыть
        </el-button>
        <el-button
          type="primary"
          size="large"
          @click="editTable(selectedTable)"
        >
          <el-icon><Edit /></el-icon>
          Редактировать
        </el-button>
      </template>
    </el-dialog>

    <!-- Диалог создания/редактирования профессиональной области -->
    <el-dialog
      v-model="profActivityDialogVisible"
      :title="editingProfActivity ? 'Редактировать область' : 'Создать область'"
      width="600px"
    >
      <el-form
        :model="profActivityForm"
        label-width="120px"
      >
        <el-form-item
          label="Код"
          required
        >
          <el-input
            v-model="profActivityForm.code"
            :disabled="!!editingProfActivity"
            placeholder="meeting_facilitation"
          />
        </el-form-item>
        <el-form-item
          label="Название"
          required
        >
          <el-input
            v-model="profActivityForm.name"
            placeholder="Проведение совещаний"
          />
        </el-form-item>
        <el-form-item label="Описание">
          <el-input
            v-model="profActivityForm.description"
            type="textarea"
            :rows="3"
            placeholder="Описание профессиональной области"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="profActivityDialogVisible = false">
          Отмена
        </el-button>
        <el-button
          v-if="editingProfActivity"
          type="danger"
          @click="deleteProfActivity"
        >
          Удалить
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="saveProfActivity"
        >
          {{ editingProfActivity ? 'Сохранить' : 'Создать' }}
        </el-button>
      </template>
    </el-dialog>
  </app-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, View, FolderAdd, Folder, Search, RefreshRight, Warning, InfoFilled, Select } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { weightsApi } from '@/api/weights'
import { profActivitiesApi } from '@/api/profActivities'
import { metricsApi } from '@/api/metrics'
import { getMetricDisplayName } from '@/utils/metricNames'
import { formatDateShort } from '@/utils/dateFormat'

// Состояние
const loading = ref(false)
const saving = ref(false)
const searchQuery = ref('')
const error = ref(null)

// Данные
const weightTables = ref([])
const profActivities = ref([])
const availableMetrics = ref([])
const warnedMetricCodes = new Set()

const resolveMetricName = (metric, fallbackCode) => {
  const code = metric?.code || fallbackCode
  const logger =
    code && warnedMetricCodes.has(code)
      ? { warn: () => {} }
      : {
          warn: (message) => {
            if (code) {
              warnedMetricCodes.add(code)
            }
            console.warn(message)
          }
        }
  return getMetricDisplayName(metric, code, logger)
}

// Диалоги
const tableDialogVisible = ref(false)
const detailsDialogVisible = ref(false)
const profActivityDialogVisible = ref(false)

const selectedTable = ref(null)
const editingTable = ref(null)
const editingProfActivity = ref(null)
const selectedWeightIndex = ref(null)

// Формы
const formRef = ref(null)
const tableForm = ref({
  prof_activity_code: '',
  weights: [],
  metadata: {
    description: ''
  }
})

const profActivityForm = ref({
  code: '',
  name: '',
  description: ''
})

// Вычисляемые свойства
const filteredAreas = computed(() => {
  // Объединяем области с их таблицами
  const areasWithTables = profActivities.value.map(activity => {
    const table = weightTables.value.find(t => t.prof_activity_code === activity.code)
    return {
      ...activity,
      weightTable: table || null
    }
  })

  // Фильтруем по поисковому запросу
  if (!searchQuery.value) {
    return areasWithTables
  }

  const query = searchQuery.value.toLowerCase()
  return areasWithTables.filter(area =>
    area.name.toLowerCase().includes(query) ||
    (area.description && area.description.toLowerCase().includes(query))
  )
})

const selectedActivityName = computed(() => {
  const activity = profActivities.value.find(a => a.code === tableForm.value.prof_activity_code)
  return activity ? activity.name : ''
})

const dialogTitle = computed(() => {
  if (editingTable.value) {
    return `Редактировать весовую таблицу: ${selectedActivityName.value}`
  }
  return `Создать весовую таблицу: ${selectedActivityName.value}`
})

const currentWeightSum = computed(() => {
  return tableForm.value.weights.reduce((sum, w) => sum + (parseFloat(w.weight) || 0), 0)
})

const isValidWeightSum = computed(() => {
  return Math.abs(currentWeightSum.value - 1.0) < 0.0001 && tableForm.value.weights.length > 0
})

const weightSumAlertType = computed(() => {
  if (Math.abs(currentWeightSum.value - 1.0) < 0.0001) return 'success'
  if (currentWeightSum.value < 1.0) return 'warning'
  return 'error'
})

const weightSumProgressStatus = computed(() => {
  if (Math.abs(currentWeightSum.value - 1.0) < 0.0001) return 'success'
  if (currentWeightSum.value > 1.0) return 'exception'
  return ''
})

const remainingWeight = computed(() => {
  return Math.max(0, 1.0 - currentWeightSum.value)
})

// Методы
const loadWeightTables = async () => {
  try {
    const data = await weightsApi.list()
    weightTables.value = data
  } catch (err) {
    console.error('Failed to load weight tables:', err)
    error.value = 'Ошибка загрузки весовых таблиц'
    ElMessage.error('Ошибка загрузки весовых таблиц')
    throw err
  }
}

const createTableForArea = (area) => {
  editingTable.value = null
  selectedWeightIndex.value = null
  tableForm.value = {
    prof_activity_code: area.code,
    weights: [],
    metadata: {
      description: ''
    }
  }
  tableDialogVisible.value = true
}

const loadProfActivities = async () => {
  try {
    const data = await profActivitiesApi.list()
    profActivities.value = data
  } catch (err) {
    console.error('Failed to load prof activities:', err)
    error.value = 'Ошибка загрузки профессиональных областей'
    ElMessage.error('Ошибка загрузки профессиональных областей')
    throw err
  }
}

const loadMetrics = async () => {
  try {
    const data = await metricsApi.listMetricDefs(true)
    availableMetrics.value = data.items || []
  } catch (err) {
    console.error('Failed to load metrics:', err)
    error.value = 'Ошибка загрузки метрик'
    ElMessage.error('Ошибка загрузки метрик')
    throw err
  }
}


const editTable = (table) => {
  editingTable.value = table
  selectedWeightIndex.value = table.weights.length > 0 ? 0 : null
  tableForm.value = {
    prof_activity_code: table.prof_activity_code,
    weights: table.weights.map(w => ({
      metric_code: w.metric_code,
      weight: parseFloat(w.weight),
      is_critical: w.is_critical || false,
      penalty: parseFloat(w.penalty) || 0,
      threshold: parseFloat(w.threshold) || 6.0
    })),
    metadata: table.metadata || { description: '' }
  }
  tableDialogVisible.value = true
}

const addWeight = () => {
  tableForm.value.weights.push({
    metric_code: '',
    weight: 0,
    is_critical: false,
    penalty: 0,
    threshold: 6.0
  })
  // Автоматически выбираем новую компетенцию
  selectedWeightIndex.value = tableForm.value.weights.length - 1
}

const selectWeight = (index) => {
  selectedWeightIndex.value = index
}

const getWeightDisplayName = (weight) => {
  if (!weight.metric_code) return 'Не выбрана'
  const metric = availableMetrics.value.find(m => m.code === weight.metric_code)
  return resolveMetricName(metric, weight.metric_code)
}

const fillRemainingWeight = () => {
  if (selectedWeightIndex.value !== null && tableForm.value.weights[selectedWeightIndex.value]) {
    const currentWeight = parseFloat(tableForm.value.weights[selectedWeightIndex.value].weight) || 0
    const remaining = 1.0 - currentWeightSum.value
    tableForm.value.weights[selectedWeightIndex.value].weight = Math.min(1, currentWeight + remaining)
  }
}

const onCriticalChange = (weight) => {
  if (!weight.is_critical) {
    weight.penalty = 0
    weight.threshold = 6.0
  }
}

const removeWeight = (index) => {
  tableForm.value.weights.splice(index, 1)
  // Обновляем выбранный индекс
  if (selectedWeightIndex.value === index) {
    selectedWeightIndex.value = tableForm.value.weights.length > 0
      ? Math.min(index, tableForm.value.weights.length - 1)
      : null
  } else if (selectedWeightIndex.value !== null && selectedWeightIndex.value > index) {
    selectedWeightIndex.value--
  }
}

const saveTable = async () => {
  try {
    saving.value = true

    // Валидация
    if (!tableForm.value.prof_activity_code) {
      ElMessage.warning('Выберите профессиональную область')
      return
    }

    if (tableForm.value.weights.length === 0) {
      ElMessage.warning('Добавьте хотя бы одну компетенцию')
      return
    }

    // Проверка уникальности метрик
    const metricCodes = tableForm.value.weights.map(w => w.metric_code)
    const uniqueCodes = new Set(metricCodes.filter(c => c))
    if (uniqueCodes.size !== tableForm.value.weights.length) {
      ElMessage.warning('Компетенции должны быть уникальными')
      return
    }

    // Проверка заполненности
    if (tableForm.value.weights.some(w => !w.metric_code)) {
      ElMessage.warning('Все компетенции должны быть заполнены')
      return
    }

    // Подготовка данных
    const payload = {
      prof_activity_code: tableForm.value.prof_activity_code,
      weights: tableForm.value.weights.map(w => ({
        metric_code: w.metric_code,
        weight: parseFloat(w.weight),
        is_critical: w.is_critical || false,
        penalty: w.is_critical ? parseFloat(w.penalty) || 0 : 0,
        threshold: w.is_critical ? parseFloat(w.threshold) || 6.0 : 6.0
      })),
      metadata: tableForm.value.metadata.description ? tableForm.value.metadata : null
    }

    // Если редактирование - используем update, иначе - upload (создание или upsert)
    if (editingTable.value) {
      await weightsApi.update(editingTable.value.id, payload)
      ElMessage.success('Изменения применены')
    } else {
      await weightsApi.upload(payload)
      ElMessage.success('Таблица создана')
    }

    tableDialogVisible.value = false
    await loadWeightTables()
  } catch (error) {
    console.error('Failed to save weight table:', error)
    ElMessage.error(error.response?.data?.detail || 'Ошибка сохранения таблицы')
  } finally {
    saving.value = false
  }
}

const viewDetails = (table) => {
  selectedTable.value = table
  detailsDialogVisible.value = true
}

const showProfActivityDialog = () => {
  editingProfActivity.value = null
  profActivityForm.value = {
    code: '',
    name: '',
    description: ''
  }
  profActivityDialogVisible.value = true
}

const editProfActivity = (activity) => {
  editingProfActivity.value = activity
  profActivityForm.value = {
    code: activity.code,
    name: activity.name,
    description: activity.description || ''
  }
  profActivityDialogVisible.value = true
}

const saveProfActivity = async () => {
  try {
    saving.value = true

    if (!profActivityForm.value.code || !profActivityForm.value.name) {
      ElMessage.warning('Заполните обязательные поля')
      return
    }

    if (editingProfActivity.value) {
      await profActivitiesApi.update(editingProfActivity.value.id, {
        name: profActivityForm.value.name,
        description: profActivityForm.value.description
      })
      ElMessage.success('Область обновлена')
    } else {
      await profActivitiesApi.create(profActivityForm.value)
      ElMessage.success('Область создана')
    }

    profActivityDialogVisible.value = false
    await loadProfActivities()
  } catch (error) {
    console.error('Failed to save prof activity:', error)
    ElMessage.error(error.response?.data?.detail || 'Ошибка сохранения области')
  } finally {
    saving.value = false
  }
}

const deleteProfActivity = async () => {
  try {
    await ElMessageBox.confirm(
      `Удалить профессиональную область "${editingProfActivity.value.name}"? Это действие нельзя отменить.`,
      'Предупреждение',
      {
        confirmButtonText: 'Удалить',
        cancelButtonText: 'Отмена',
        type: 'error'
      }
    )

    await profActivitiesApi.delete(editingProfActivity.value.id)
    ElMessage.success('Область удалена')
    profActivityDialogVisible.value = false
    await loadProfActivities()
    await loadWeightTables()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete prof activity:', error)
      ElMessage.error(error.response?.data?.detail || 'Ошибка удаления области')
    }
  }
}

const calculateWeightSum = (table) => {
  return table.weights.reduce((sum, w) => sum + parseFloat(w.weight), 0)
}

const getWeightSumType = (table) => {
  const sum = calculateWeightSum(table)
  if (Math.abs(sum - 1.0) < 0.0001) return 'success'
  return 'danger'
}

const enrichedWeights = (weights) => {
  return weights.map(w => {
    const metric = availableMetrics.value.find(m => m.code === w.metric_code)
    return {
      ...w,
      metric_name: resolveMetricName(metric, w.metric_code),
      metric_code: w.metric_code,
      is_critical: w.is_critical || false,
      penalty: w.penalty || 0,
      threshold: w.threshold || 6.0
    }
  })
}

// Используем formatDateShort для краткого формата даты
const formatDate = formatDateShort

// Загрузка всех данных
const loadData = async () => {
  loading.value = true
  error.value = null
  try {
    await Promise.all([
      loadWeightTables(),
      loadProfActivities(),
      loadMetrics()
    ])
  } catch (err) {
    console.error('Failed to load data:', err)
    if (!error.value) {
      error.value = 'Не удалось загрузить данные'
    }
  } finally {
    loading.value = false
  }
}

// Инициализация
onMounted(async () => {
  await loadData()
})
</script>

<style scoped>
.admin-weights-view {
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

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-buttons {
  display: flex;
  gap: var(--spacing-md);
}

.header-card h1 {
  font-size: var(--font-size-h1);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.header-card p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.icon-primary {
  color: var(--color-primary);
}

/* Search Card */
.search-card {
  margin-bottom: var(--spacing-2xl);
}

/* Areas Grid */
.areas-container {
  min-height: 300px;
}

.areas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: var(--spacing-2xl);
}

.area-card-wrapper {
  min-height: 200px;
}

.area-card {
  height: 100%;
  transition: var(--transition-base);
}

.area-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

/* Area Header */
.area-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-sm);
}

.area-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex: 1;
}

.area-title h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.area-description {
  margin-top: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

/* Table Info */
.no-table {
  padding: var(--spacing-xl);
  text-align: center;
}

.table-info {
  padding: var(--spacing-lg) 0;
}

.table-stats {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background-color: var(--color-bg-section);
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-border-lighter);
}

.stat-label {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-regular);
  font-size: var(--font-size-sm);
}

.table-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
}

/* Dialog Styles */
.area-display-card {
  background-color: var(--color-primary-bg);
  border: 1px solid var(--color-primary-lighter);
}

.area-display-card :deep(.el-card__body) {
  padding: var(--spacing-md);
}

.selected-area {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.area-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.table-summary-card {
  background-color: var(--color-bg-section);
  margin-bottom: var(--spacing-xl);
}

.metric-cell {
  padding: var(--spacing-sm) 0;
}

.metadata-card {
  background-color: var(--color-bg-section);
  line-height: var(--line-height-relaxed);
}

.metadata-card :deep(.el-card__body) {
  padding: var(--spacing-lg);
}

/* Weight Sum Indicator */
.weight-sum-indicator {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md) var(--spacing-lg);
  background-color: var(--color-white);
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-border-light);
}

.weight-sum-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.weight-sum-label {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-regular);
}

.weight-sum-value {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.weight-sum-remaining {
  margin-left: auto;
  font-size: var(--font-size-sm);
  color: var(--color-warning);
}

.weight-sum-remaining.is-over {
  color: var(--color-danger);
}

/* Weights Editor Grid - Two Column Layout */
.weights-editor-grid {
  display: grid;
  grid-template-columns: 40% 60%;
  gap: var(--spacing-lg);
  min-height: 400px;
}

/* Left Column - Competency List */
.competency-list {
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-section);
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
}

.competency-list-header {
  padding: var(--spacing-md) var(--spacing-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  background-color: var(--color-white);
  border-bottom: 1px solid var(--color-border-light);
}

.competency-list-items {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.competency-list-item {
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
  background-color: var(--color-white);
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-border-lighter);
  cursor: pointer;
  transition: var(--transition-fast);
}

.competency-list-item:hover {
  border-color: var(--color-primary-lighter);
  background-color: var(--color-primary-bg);
}

.competency-list-item.is-selected {
  border-color: var(--color-primary);
  background-color: var(--color-primary-bg);
  box-shadow: 0 0 0 2px var(--color-focus-ring);
}

.competency-item-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.critical-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.competency-name {
  flex: 1;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.competency-weight {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.competency-percent {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.competency-list-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-2xl);
}

.add-competency-btn {
  margin: var(--spacing-md);
}

/* Right Column - Competency Detail */
.competency-detail {
  background-color: var(--color-white);
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-xl);
  overflow-y: auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border-light);
}

.detail-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.detail-section {
  margin-bottom: var(--spacing-xl);
}

.detail-label {
  display: block;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-regular);
  margin-bottom: var(--spacing-sm);
}

.detail-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.detail-label-row .detail-label {
  margin-bottom: 0;
}

.detail-select {
  width: 100%;
}

.metric-code-hint {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.weight-input {
  width: 100px;
}

.weight-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-sm);
}

.remaining-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* Critical Section */
.critical-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background-color: var(--color-bg-section);
  border-radius: var(--border-radius-base);
  margin-bottom: var(--spacing-md);
}

.critical-toggle-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.critical-params {
  padding: var(--spacing-lg);
  background-color: var(--color-danger-light);
  border-radius: var(--border-radius-base);
  border: 1px dashed var(--color-danger);
}

.critical-param {
  margin-bottom: var(--spacing-lg);
}

.critical-param:last-of-type {
  margin-bottom: var(--spacing-md);
}

.penalty-input,
.threshold-input {
  width: 90px;
}

.threshold-value {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.threshold-unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.critical-hint {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* Empty State */
.detail-empty {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  text-align: center;
  color: var(--color-text-secondary);
}

.detail-empty p {
  margin: var(--spacing-md) 0 0 0;
  font-size: var(--font-size-base);
}

.detail-empty-hint {
  font-size: var(--font-size-sm);
  color: var(--color-text-placeholder);
}

/* Dialog specific */
.weights-dialog :deep(.el-dialog__body) {
  padding: var(--spacing-lg) var(--spacing-xl);
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

/* Dialog styling */
:deep(.el-dialog) {
  border-radius: var(--border-radius-xl);
  box-shadow: var(--shadow-xl);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border-light);
  padding: var(--spacing-xl) var(--spacing-xl) var(--spacing-lg);
}

:deep(.el-dialog__title) {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-xl);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--color-border-light);
  padding: var(--spacing-lg) var(--spacing-xl);
}

/* Descriptions styling */
:deep(.el-descriptions) {
  --el-descriptions-item-bordered-label-background: var(--color-bg-section);
}

/* Responsive */
@media (max-width: 900px) {
  .areas-grid {
    grid-template-columns: 1fr;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-lg);
  }

  .weights-editor-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }

  .competency-list {
    max-height: 250px;
  }

  .competency-detail {
    min-height: 400px;
  }
}
</style>
