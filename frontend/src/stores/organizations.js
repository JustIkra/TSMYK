/**
 * Organizations Store
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { organizationsApi } from '@/api'
import { normalizeApiError } from '@/utils/normalizeError'

export const useOrganizationsStore = defineStore('organizations', () => {
  const organizations = ref([])
  const currentOrganization = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({
    total: 0,
    page: 1,
    size: 20,
    totalPages: 0
  })

  async function searchOrganizations(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await organizationsApi.search(params)
      organizations.value = data.items
      pagination.value = {
        total: data.total,
        page: data.page,
        size: data.size,
        totalPages: Math.ceil(data.total / data.size)
      }
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка загрузки организаций')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getOrganization(orgId) {
    loading.value = true
    error.value = null
    try {
      const data = await organizationsApi.getById(orgId)
      currentOrganization.value = data
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка загрузки организации')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createOrganization(orgData) {
    loading.value = true
    error.value = null
    try {
      const data = await organizationsApi.create(orgData)
      organizations.value.unshift(data)
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка создания организации')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateOrganization(orgId, orgData) {
    loading.value = true
    error.value = null
    try {
      const data = await organizationsApi.update(orgId, orgData)
      const index = organizations.value.findIndex(o => o.id === orgId)
      if (index !== -1) {
        organizations.value[index] = data
      }
      if (currentOrganization.value?.id === orgId) {
        currentOrganization.value = { ...currentOrganization.value, ...data }
      }
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка обновления организации')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteOrganization(orgId) {
    loading.value = true
    error.value = null
    try {
      await organizationsApi.delete(orgId)
      organizations.value = organizations.value.filter(o => o.id !== orgId)
      if (currentOrganization.value?.id === orgId) {
        currentOrganization.value = null
      }
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка удаления организации')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    organizations,
    currentOrganization,
    loading,
    error,
    pagination,
    searchOrganizations,
    getOrganization,
    createOrganization,
    updateOrganization,
    deleteOrganization
  }
})
