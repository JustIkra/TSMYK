<template>
  <AppLayout>
    <div class="profile-container">
      <el-card class="profile-card">
        <template #header>
          <div class="card-header">
            <h2>Профиль</h2>
            <p>Редактирование личной информации</p>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
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
              :type="authStore.isAdmin ? 'danger' : 'info'"
              size="large"
            >
              {{ authStore.isAdmin ? 'ADMIN' : 'USER' }}
            </el-tag>
          </el-form-item>

          <el-form-item>
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
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores'
import AppLayout from '@/components/AppLayout.vue'

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
}

.profile-card {
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

.form-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
}
</style>
