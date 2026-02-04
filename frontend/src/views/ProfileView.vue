<template>
  <AppLayout>
    <div class="profile-container">
      <div class="page-header">
        <h1 class="page-title">
          Профиль
        </h1>
        <p class="page-subtitle">
          Редактирование личной информации
        </p>
      </div>

      <div class="card profile-card">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="profile-form"
          @submit.prevent="handleSave"
        >
          <el-form-item label="Email">
            <el-input
              :model-value="authStore.user?.email"
              disabled
              size="large"
            />
            <div class="form-hint">
              Email нельзя изменить
            </div>
          </el-form-item>

          <el-form-item
            label="ФИО"
            prop="fullName"
          >
            <el-input
              v-model="form.fullName"
              placeholder="Введите ФИО"
              size="large"
              maxlength="255"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="Роль">
            <el-tag
              :type="getRoleTagType(authStore.user?.role)"
              size="large"
              class="role-tag"
            >
              {{ getRoleLabel(authStore.user?.role) }}
            </el-tag>
          </el-form-item>

          <el-form-item class="form-actions">
            <el-button
              type="primary"
              size="large"
              :loading="authStore.loading"
              @click="handleSave"
            >
              Сохранить
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores'
import AppLayout from '@/components/AppLayout.vue'
import { getRoleLabel, getRoleTagType } from '@/utils/labels'

const authStore = useAuthStore()
const formRef = ref(null)

const form = reactive({
  fullName: ''
})

const rules = {
  fullName: [
    { required: true, message: 'Введите ФИО', trigger: 'blur' },
    { max: 255, message: 'Максимум 255 символов', trigger: 'blur' }
  ]
}

onMounted(() => {
  form.fullName = authStore.user?.full_name || ''
})

const handleSave = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await authStore.updateProfile(form.fullName)
      ElMessage.success('Профиль успешно обновлен')
    } catch (error) {
      ElMessage.error(authStore.error || 'Ошибка обновления профиля')
    }
  })
}
</script>

<style scoped>
.profile-container {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

.page-header {
  margin-bottom: var(--spacing-xl);
}

.page-title {
  font-size: var(--font-size-h1);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.page-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

.profile-card {
  background-color: var(--color-bg-card);
  border: 1px solid var(--card-border-color);
  border-radius: var(--card-border-radius);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-2xl);
}

.profile-form {
  max-width: 100%;
}

.form-hint {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.form-actions {
  margin-bottom: 0;
  padding-top: var(--spacing-md);
}

/* Form item spacing */
:deep(.el-form-item) {
  margin-bottom: var(--spacing-xl);
}

:deep(.el-form-item__label) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  padding-bottom: var(--spacing-xs);
}

/* Input styling */
:deep(.el-input__wrapper) {
  border-radius: var(--input-border-radius);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  transition: var(--transition-fast);
  background-color: var(--color-white);
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border-dark) inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-focus-ring);
}

:deep(.el-input__wrapper.is-disabled) {
  background-color: var(--color-gray-50);
  cursor: not-allowed;
}

:deep(.el-input__inner) {
  font-size: var(--font-size-base);
}

/* Tag styling - not pill-shaped */
.role-tag {
  border-radius: var(--border-radius-base);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-weight: var(--font-weight-medium);
}

/* Button styling - not pill-shaped */
:deep(.el-button) {
  border-radius: var(--button-border-radius);
  font-weight: var(--button-font-weight);
  transition: var(--transition-button);
}

:deep(.el-button--primary) {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}

:deep(.el-button--primary:hover) {
  background-color: var(--color-primary-dark);
  border-color: var(--color-primary-dark);
}

@media (max-width: 768px) {
  .profile-container {
    padding: var(--spacing-lg);
  }

  .profile-card {
    padding: var(--spacing-xl);
  }

  .page-title {
    font-size: var(--font-size-h2);
  }
}
</style>
