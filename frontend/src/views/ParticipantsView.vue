<template>
  <app-layout>
    <div class="participants-view">
      <el-card class="header-card">
        <div class="header-content">
          <h1>Участники</h1>
          <el-button
            type="primary"
            @click="showCreateDialog = true"
          >
            <el-icon><Plus /></el-icon>
            Добавить участника
          </el-button>
        </div>
      </el-card>

      <el-card class="search-card">
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
      </el-card>

      <el-card
        v-loading="participantsStore.loading"
        class="table-card"
      >
        <!-- Desktop Table View -->
        <el-table
          v-if="!isMobile"
          :data="participantsStore.participants"
          stripe
        >
          <el-table-column
            prop="full_name"
            label="ФИО"
            min-width="200"
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
            width="180"
            fixed="right"
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
                  class="actions-group__danger"
                  type="danger"
                  size="small"
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
          <el-card
            v-for="participant in participantsStore.participants"
            :key="participant.id"
            class="participant-card"
            shadow="hover"
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
                @click="confirmDelete(participant)"
              >
                Удалить
              </el-button>
            </div>
          </el-card>

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
      </el-card>

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
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import AppLayout from '@/components/AppLayout.vue'
import { useParticipantsStore } from '@/stores'

const router = useRouter()
const participantsStore = useParticipantsStore()

// Responsive
const isMobile = ref(window.innerWidth <= 768)
const updateMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

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
  window.addEventListener('resize', updateMobile)
  handleSearch()
})

onUnmounted(() => {
  window.removeEventListener('resize', updateMobile)
})
</script>

<style scoped>
.participants-view {
  max-width: 1400px;
  margin: 0 auto;
}

.header-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0;
  font-size: 24px;
  color: var(--color-text-primary);
}

.header-content .el-button {
  min-height: 44px;
}

.search-card {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.actions-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.actions-group .el-button {
  width: 140px;
  justify-content: center;
  margin: 0;
}

.actions-group__danger {
  margin: 0;
}

.pagination--mobile {
  justify-content: center;
}

/* Mobile Card Styles */
.participants-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.participant-card {
  width: 100%;
}

.participant-card__name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.participant-card__info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.participant-card__field {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-label {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.field-value {
  color: var(--color-text-primary);
  font-weight: 500;
}

.participant-card__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.participant-card__actions .el-button {
  width: 100%;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 12px;
  }

  .header-content h1 {
    font-size: 20px;
  }

  .search-card :deep(.el-form-item) {
    width: 100%;
    margin-right: 0;
    margin-bottom: 12px;
  }

  .search-card :deep(.el-form-item__content) {
    width: 100%;
  }
}
</style>
