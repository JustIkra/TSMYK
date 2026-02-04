<template>
  <AppLayout>
    <div class="settings-container">
      <div class="page-header">
        <h1 class="page-title">
          Настройки
        </h1>
        <p class="page-subtitle">
          Управление учетной записью
        </p>
      </div>

      <div class="card settings-card">
        <div class="card-header">
          <h2 class="card-title">
            Смена пароля
          </h2>
          <p class="card-subtitle">
            Обновите пароль для вашей учетной записи
          </p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleChangePassword"
        >
          <el-form-item
            label="Текущий пароль"
            prop="currentPassword"
          >
            <el-input
              v-model="form.currentPassword"
              type="password"
              placeholder="Введите текущий пароль"
              size="large"
              show-password
              autocomplete="current-password"
            />
          </el-form-item>

          <el-form-item
            label="Новый пароль"
            prop="newPassword"
          >
            <el-input
              v-model="form.newPassword"
              type="password"
              placeholder="Введите новый пароль (минимум 8 символов, буква и цифра)"
              size="large"
              show-password
              autocomplete="new-password"
            />
          </el-form-item>

          <el-form-item
            label="Подтверждение нового пароля"
            prop="confirmPassword"
          >
            <el-input
              v-model="form.confirmPassword"
              type="password"
              placeholder="Повторите новый пароль"
              size="large"
              show-password
              autocomplete="new-password"
              @keyup.enter="handleChangePassword"
            />
          </el-form-item>

          <el-form-item class="form-actions">
            <el-button
              type="primary"
              size="large"
              :loading="authStore.loading"
              @click="handleChangePassword"
            >
              Сменить пароль
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores'
import AppLayout from '@/components/AppLayout.vue'

const authStore = useAuthStore()
const formRef = ref(null)

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validatePassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Введите новый пароль'))
  } else if (value.length < 8) {
    callback(new Error('Пароль должен быть не менее 8 символов'))
  } else if (!/[a-zA-Z]/.test(value)) {
    callback(new Error('Пароль должен содержать хотя бы одну букву'))
  } else if (!/\d/.test(value)) {
    callback(new Error('Пароль должен содержать хотя бы одну цифру'))
  } else {
    callback()
  }
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Подтвердите новый пароль'))
  } else if (value !== form.newPassword) {
    callback(new Error('Пароли не совпадают'))
  } else {
    callback()
  }
}

const rules = {
  currentPassword: [
    { required: true, message: 'Введите текущий пароль', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const resetForm = () => {
  form.currentPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
  formRef.value?.clearValidate()
}

const handleChangePassword = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await authStore.changePassword(form.currentPassword, form.newPassword)
      ElMessage.success('Пароль успешно изменен')
      resetForm()
    } catch (error) {
      const errorMessage = authStore.error || 'Ошибка смены пароля'
      ElMessage.error(errorMessage)
    }
  })
}
</script>

<style scoped>
.settings-container {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

/* Card styling - uses .card from theme-tokens.css */
.settings-card {
  margin-top: var(--spacing-lg);
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
  border-radius: var(--border-radius-base);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  transition: var(--transition-fast);
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-gray-400) inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-focus-ring);
}

/* Button styling - standard rounded corners, not pill-shaped */
.form-actions {
  margin-top: var(--spacing-2xl);
  margin-bottom: 0;
}

.form-actions :deep(.el-button) {
  border-radius: var(--border-radius-base);
  min-width: 160px;
}

@media (max-width: 768px) {
  .settings-container {
    padding: var(--spacing-lg);
  }

  .form-actions :deep(.el-button) {
    width: 100%;
  }
}
</style>
