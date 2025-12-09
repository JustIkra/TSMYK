<template>
  <AppLayout>
    <div class="settings-container">
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <h2>Настройки</h2>
            <p>Смена пароля</p>
          </div>
        </template>

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

          <el-form-item>
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
      </el-card>
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
}

.settings-card {
  box-shadow: var(--shadow-md);
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0 0 8px 0;
  color: var(--color-primary);
  font-size: 24px;
}

.card-header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}
</style>
