import apiClient from './client'

export const scoringApi = {
  /**
   * Get all scoring results for a participant
   * @param {string} participantId - Participant UUID
   * @returns {Promise<Object>} - Scoring results list
   */
  async getParticipantScores(participantId) {
    const response = await apiClient.get(`/scoring/participants/${participantId}`)
    return response.data
  },

  /**
   * Recalculate scoring for a participant
   * @param {string} participantId - Participant UUID
   * @param {Array<string>|null} weightTableIds - Optional specific weight tables
   * @returns {Promise<Array>} - Updated scoring results
   */
  async recalculateParticipant(participantId, weightTableIds = null) {
    const response = await apiClient.post(
      `/scoring/participants/${participantId}/recalculate`,
      weightTableIds ? { weight_table_ids: weightTableIds } : {}
    )
    return response.data
  },

  /**
   * Calculate single score for participant and weight table
   * @param {string} participantId - Participant UUID
   * @param {string} weightTableId - Weight table UUID
   * @returns {Promise<Object>} - Scoring result
   */
  async calculateSingle(participantId, weightTableId) {
    const response = await apiClient.post(
      `/scoring/participants/${participantId}/calculate/${weightTableId}`
    )
    return response.data
  },

  /**
   * Batch recalculate scoring
   * @param {Object} params - Batch parameters
   * @param {Array<string>|null} params.participantIds - Optional participant IDs
   * @param {Array<string>|null} params.weightTableIds - Optional weight table IDs
   * @returns {Promise<Object>} - Batch result with counts
   */
  async batchRecalculate({ participantIds = null, weightTableIds = null } = {}) {
    const response = await apiClient.post('/scoring/batch/recalculate', {
      participant_ids: participantIds,
      weight_table_ids: weightTableIds
    })
    return response.data
  }
}
