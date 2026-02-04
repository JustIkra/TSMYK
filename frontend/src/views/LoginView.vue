<template>
  <div class="login-container">
    <el-card
      class="login-card"
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
                id="logoGradient"
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
              fill="url(#logoGradient)"
            />
            <path
              d="M14 24L21 31L34 18"
              stroke="white"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </div>
        <h2>Вход в систему</h2>
        <p>Цифровая модель универсальных компетенций</p>
      </div>

      <el-alert
        v-if="route.query.message === 'pending'"
        title="Ожидание одобрения"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        Ваш аккаунт ожидает одобрения администратором.
      </el-alert>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
        @validate="onFieldValidate"
      >
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
            placeholder="Введите пароль"
            size="large"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="authStore.loading"
            @click="handleLogin"
          >
            Войти
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

        <div class="register-link">
          <span>Нет аккаунта?</span>
          <router-link to="/register">
            Зарегистрироваться
          </router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores'
import { useFieldErrorAnimation } from '@/composables/useFieldErrorAnimation'
import { ElMessage } from 'element-plus'
import { normalizeApiError } from '@/utils/normalizeError'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref(null)
const form = reactive({
  email: '',
  password: ''
})

const authFields = ['email', 'password']
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

const rules = {
  email: [
    { required: true, message: 'Введите email', trigger: 'blur' },
    { type: 'email', message: 'Некорректный email', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Введите пароль', trigger: 'blur' },
    { min: 8, message: 'Пароль должен быть не менее 8 символов', trigger: 'blur' }
  ]
}

const onFieldValidate = (prop, isValid) => {
  handleFieldValidate(prop, isValid)
  if (isValid && serverErrors.value.length) {
    serverErrors.value = []
  }
}

const handleLogin = async () => {
  if (!formRef.value) return

  serverErrors.value = []

  await formRef.value.validate(async (valid, fields) => {
    if (!valid) {
      handleValidationErrors(fields)
      return
    }

    try {
      await authStore.login(form.email, form.password)
      ElMessage.success('Вход выполнен успешно')
      const redirect = route.query.redirect || '/participants'
      router.push(redirect)
    } catch (error) {
      const normalized = error.normalizedError || normalizeApiError(error, authStore.error || 'Ошибка входа')
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
  () => [form.email, form.password],
  () => {
    if (serverErrors.value.length) {
      serverErrors.value = []
    }
  }
)
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-hero);
  padding: var(--spacing-xl);
}

.login-card {
  width: 100%;
  max-width: 440px;
  border-radius: var(--border-radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  background-color: var(--color-bg-card);
}

.login-card :deep(.el-card__body) {
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
.login-card :deep(.el-input__wrapper) {
  border-radius: var(--border-radius-base);
  box-shadow: 0 0 0 1px var(--color-border-light) inset;
  transition: var(--transition-fast);
}

.login-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border) inset;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-focus-ring);
}

/* Button styling - non-pill shape */
.login-card :deep(.el-button) {
  border-radius: var(--border-radius-base);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-button);
}

.login-card :deep(.el-button--primary) {
  background: var(--gradient-primary);
  border-color: var(--color-primary);
}

.login-card :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-primary-darker) 100%);
  border-color: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.login-card :deep(.el-button--primary:active) {
  transform: translateY(0);
}

/* Form label styling */
.login-card :deep(.el-form-item__label) {
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.register-link {
  text-align: center;
  color: var(--color-text-secondary);
  margin-top: var(--spacing-lg);
  font-size: var(--font-size-base);
}

.register-link a {
  color: var(--color-primary);
  text-decoration: none;
  margin-left: var(--spacing-xs);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-fast);
}

.register-link a:hover {
  color: var(--color-primary-dark);
  text-decoration: underline;
}
</style>
