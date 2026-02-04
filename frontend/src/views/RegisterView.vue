<template>
  <div class="register-container">
    <el-card
      class="register-card"
      shadow="never"
    >
      <div class="card-header">
        <div class="logo-icon">
          <svg
            width="48"
            height="48"
            viewBox="0 0 48 48"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient
                id="logoGradientReg"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="100%"
              >
                <stop
                  offset="0%"
                  style="stop-color:#4F6AF0"
                />
                <stop
                  offset="100%"
                  style="stop-color:#3D56D4"
                />
              </linearGradient>
            </defs>
            <rect
              width="48"
              height="48"
              rx="12"
              fill="url(#logoGradientReg)"
            />
            <path
              d="M16 24L22 30L32 18"
              stroke="white"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </div>
        <h2>Регистрация</h2>
        <p>Создайте аккаунт для работы с системой</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
        @validate="onFieldValidate"
      >
        <el-form-item
          label="ФИО"
          prop="fullName"
          :class="getFormItemClass('fullName')"
        >
          <el-input
            v-model="form.fullName"
            placeholder="Иванов Иван Иванович (необязательно)"
            size="large"
            autocomplete="name"
          />
        </el-form-item>

        <el-form-item
          label="Email"
          prop="email"
          :class="getFormItemClass('email')"
        >
          <el-input
            v-model="form.email"
            type="email"
            placeholder="Введите email"
            size="large"
            autocomplete="email"
          />
        </el-form-item>

        <el-form-item
          label="Пароль"
          prop="password"
          :class="getFormItemClass('password')"
        >
          <el-input
            v-model="form.password"
            type="password"
            placeholder="Введите пароль (минимум 8 символов, буквы и цифры)"
            size="large"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item
          label="Подтверждение пароля"
          prop="confirmPassword"
          :class="getFormItemClass('confirmPassword')"
        >
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="Повторите пароль"
            size="large"
            show-password
            autocomplete="new-password"
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="authStore.loading"
            @click="handleRegister"
          >
            Зарегистрироваться
          </el-button>
        </el-form-item>

        <div
          v-if="serverErrors.length"
          :class="['auth-form-error', { 'auth-field-animate': serverErrorAnimated }]"
          role="alert"
        >
          <span
            class="auth-form-error__icon"
            aria-hidden="true"
          >
            !
          </span>
          <div class="auth-form-error__content">
            <template v-if="serverErrors.length === 1">
              {{ serverErrors[0] }}
            </template>
            <template v-else>
              <ul class="auth-form-error__list">
                <li
                  v-for="(message, index) in serverErrors"
                  :key="index"
                >
                  {{ message }}
                </li>
              </ul>
            </template>
          </div>
        </div>

        <div class="login-link">
          <span>Уже есть аккаунт?</span>
          <router-link to="/login">
            Войти
          </router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores'
import { useFieldErrorAnimation } from '@/composables/useFieldErrorAnimation'
import { normalizeApiError } from '@/utils/normalizeError'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref(null)
const form = reactive({
  fullName: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const authFields = ['fullName', 'email', 'password', 'confirmPassword']

const {
  getFormItemClass,
  handleValidationErrors,
  handleFieldValidate,
  triggerForFields,
  markExternalErrors
} = useFieldErrorAnimation(authFields)

const serverErrors = ref([])
const serverErrorAnimated = ref(false)

const restartServerErrorAnimation = () => {
  serverErrorAnimated.value = false
  nextTick(() => {
    serverErrorAnimated.value = true
    setTimeout(() => {
      serverErrorAnimated.value = false
    }, 360)
  })
}

const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Подтвердите пароль'))
  } else if (value !== form.password) {
    callback(new Error('Пароли не совпадают'))
  } else {
    callback()
  }
}

const rules = {
  email: [
    { required: true, message: 'Введите email', trigger: 'blur' },
    { type: 'email', message: 'Некорректный email', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Введите пароль', trigger: 'blur' },
    { min: 8, message: 'Пароль должен быть не менее 8 символов', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const onFieldValidate = (prop, isValid) => {
  handleFieldValidate(prop, isValid)
  if (isValid && serverErrors.value.length) {
    serverErrors.value = []
  }
}

const handleRegister = async () => {
  if (!formRef.value) return

  serverErrors.value = []

  await formRef.value.validate(async (valid, fields) => {
    if (!valid) {
      handleValidationErrors(fields)
      return
    }

    try {
      const fullName = form.fullName.trim() || null
      await authStore.register(form.email, form.password, fullName)
      ElMessage.success({
        message: 'Регистрация успешна! Ожидайте одобрения администратора.',
        duration: 5000
      })
      router.push('/login?message=pending')
    } catch (error) {
      const normalized = error.normalizedError || normalizeApiError(error, authStore.error || 'Ошибка регистрации')
      serverErrors.value = normalized.messages
      const fieldsWithErrors = Object.keys(normalized.fieldErrors)
      const fieldsToMark = fieldsWithErrors.length ? fieldsWithErrors : authFields
      markExternalErrors(fieldsToMark)
      triggerForFields(fieldsToMark)
      restartServerErrorAnimation()
    }
  })
}

watch(
  () => [form.fullName, form.email, form.password, form.confirmPassword],
  () => {
    if (serverErrors.value.length) {
      serverErrors.value = []
    }
  }
)
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-hero);
  padding: var(--spacing-xl);
}

.register-card {
  width: 100%;
  max-width: 450px;
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  background-color: var(--color-bg-card);
}

.register-card :deep(.el-card__body) {
  padding: var(--spacing-3xl);
}

.card-header {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.logo-icon {
  display: flex;
  justify-content: center;
  margin-bottom: var(--spacing-lg);
}

.card-header h2 {
  margin: 0 0 var(--spacing-sm) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-h1);
  font-weight: var(--font-weight-semibold);
}

.card-header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

/* Input styling */
.register-card :deep(.el-input__wrapper) {
  border-radius: var(--border-radius-base);
  box-shadow: 0 0 0 1px var(--color-border-light) inset;
  transition: var(--transition-fast);
}

.register-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border) inset;
}

.register-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-focus-ring);
}

/* Button styling - non-pill shape */
.register-card :deep(.el-button) {
  border-radius: var(--border-radius-base);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-button);
}

.register-card :deep(.el-button--primary) {
  background: var(--gradient-primary);
  border-color: var(--color-primary);
}

.register-card :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary-darker) 100%);
  border-color: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.register-card :deep(.el-button--primary:active) {
  transform: translateY(0);
}

/* Form label styling */
.register-card :deep(.el-form-item__label) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.login-link {
  text-align: center;
  color: var(--color-text-secondary);
  margin-top: var(--spacing-lg);
  font-size: var(--font-size-base);
}

.login-link a {
  color: var(--color-primary);
  text-decoration: none;
  margin-left: var(--spacing-xs);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-fast);
}

.login-link a:hover {
  color: var(--color-primary-dark);
  text-decoration: underline;
}
</style>
