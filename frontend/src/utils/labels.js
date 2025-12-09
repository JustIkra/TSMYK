/**
 * Локализация ролей и статусов пользователей
 */

export const ROLE_LABELS = {
  ADMIN: 'Администратор',
  USER: 'Пользователь',
  SUPERVISOR: 'Супервайзер',
  ANALYST: 'Аналитик'
}

export const STATUS_LABELS = {
  ACTIVE: 'Активен',
  PENDING: 'Ожидает',
  BLOCKED: 'Заблокирован'
}

/**
 * Цветовые темы для бейджей Element Plus
 * Использует нейтральные цвета вместо красного danger для обычных ролей
 */
export const ROLE_TAG_TYPES = {
  ADMIN: 'primary',    // синий — авторитет, но не угроза
  USER: '',            // серый/дефолтный — обычный пользователь
  SUPERVISOR: 'warning',
  ANALYST: 'info'
}

export const STATUS_TAG_TYPES = {
  ACTIVE: 'success',
  PENDING: 'warning',
  BLOCKED: 'danger'
}

/**
 * Получить русское название роли
 * @param {string} role - код роли (ADMIN, USER, ...)
 * @returns {string} локализованное название
 */
export function getRoleLabel(role) {
  return ROLE_LABELS[role] || role
}

/**
 * Получить русское название статуса
 * @param {string} status - код статуса (ACTIVE, PENDING, ...)
 * @returns {string} локализованное название
 */
export function getStatusLabel(status) {
  return STATUS_LABELS[status] || status
}

/**
 * Получить тип тега для роли
 * @param {string} role - код роли
 * @returns {string} тип тега Element Plus
 */
export function getRoleTagType(role) {
  return ROLE_TAG_TYPES[role] || ''
}

/**
 * Получить тип тега для статуса
 * @param {string} status - код статуса
 * @returns {string} тип тега Element Plus
 */
export function getStatusTagType(status) {
  return STATUS_TAG_TYPES[status] || 'info'
}
