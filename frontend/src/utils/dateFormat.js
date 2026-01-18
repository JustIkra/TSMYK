/**
 * Форматирует дату в локализованный формат
 * @param {string|Date} date - Дата для форматирования
 * @param {Object} options - Опции форматирования (по умолчанию включают год, месяц, день, часы и минуты)
 * @returns {string} Отформатированная дата или '—' если дата невалидна
 */
export function formatDate(date, options = null) {
  if (!date) return '—'

  const parsedDate = new Date(date)
  if (Number.isNaN(parsedDate.getTime())) return '—'

  const defaultOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }

  return parsedDate.toLocaleString('ru-RU', options || defaultOptions)
}

/**
 * Форматирует дату в более развернутом формате (с названием месяца)
 * @param {string|Date} date - Дата для форматирования
 * @returns {string} Отформатированная дата или '—' если дата невалидна
 */
export function formatDateLong(date) {
  if (!date) return '—'

  const parsedDate = new Date(date)
  if (Number.isNaN(parsedDate.getTime())) return '—'

  return parsedDate.toLocaleString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Форматирует только дату без времени
 * @param {string|Date} date - Дата для форматирования
 * @returns {string} Отформатированная дата или '—' если дата невалидна
 */
export function formatDateShort(date) {
  if (!date) return '—'

  const parsedDate = new Date(date)
  if (Number.isNaN(parsedDate.getTime())) return '—'

  return parsedDate.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
