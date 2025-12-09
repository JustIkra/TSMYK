/**
 * Admin Store - управление пользователями (админ)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { adminApi } from '@/api'
import { normalizeApiError } from '@/utils/normalizeError'

export const useAdminStore = defineStore('admin', () => {
  const pendingUsers = ref([])
  const users = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchPendingUsers() {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.getPendingUsers()
      pendingUsers.value = data
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка загрузки пользователей')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAllUsers() {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.getAllUsers()
      users.value = data
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка загрузки списка пользователей')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function approveUser(userId) {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.approveUser(userId)
      pendingUsers.value = pendingUsers.value.filter(u => u.id !== userId)
      // Обновим пользователя в общем списке, если он уже загружен
      users.value = users.value.map((u) => (u.id === userId ? data : u))
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка одобрения пользователя')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function makeAdmin(userId) {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.makeAdmin(userId)
      users.value = users.value.map((u) => (u.id === userId ? data : u))
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка назначения прав администратора')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteUser(userId) {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.deleteUser(userId)
      users.value = users.value.filter((u) => u.id !== userId)
      pendingUsers.value = pendingUsers.value.filter((u) => u.id !== userId)
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка удаления пользователя')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function revokeAdmin(userId) {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.revokeAdmin(userId)
      users.value = users.value.map((u) => (u.id === userId ? data : u))
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка снятия прав администратора')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    pendingUsers,
    users,
    loading,
    error,
    fetchPendingUsers,
    fetchAllUsers,
    approveUser,
    makeAdmin,
    revokeAdmin,
    deleteUser
  }
})
