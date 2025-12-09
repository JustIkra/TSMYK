/**
 * Admin API endpoints
 */

import apiClient from './client'

export const adminApi = {
  /**
   * Получить список пользователей со статусом PENDING
   */
  async getPendingUsers() {
    const response = await apiClient.get('/admin/pending-users')
    return response.data
  },

  /**
   * Получить список всех пользователей
   */
  async getAllUsers() {
    const response = await apiClient.get('/admin/users')
    return response.data
  },

  /**
   * Одобрить пользователя (PENDING -> ACTIVE)
   * @param {string} userId - UUID
   */
  async approveUser(userId) {
    const response = await apiClient.post(`/admin/approve/${userId}`)
    return response.data
  },

  /**
   * Назначить пользователя администратором
   * @param {string} userId - UUID
   */
  async makeAdmin(userId) {
    const response = await apiClient.post(`/admin/make-admin/${userId}`)
    return response.data
  },

  /**
   * Удалить пользователя
   * @param {string} userId - UUID
   */
  async deleteUser(userId) {
    const response = await apiClient.delete(`/admin/users/${userId}`)
    return response.data
  },

  /**
   * Снять права администратора
   * @param {string} userId - UUID
   */
  async revokeAdmin(userId) {
    const response = await apiClient.post(`/admin/revoke-admin/${userId}`)
    return response.data
  }
}
