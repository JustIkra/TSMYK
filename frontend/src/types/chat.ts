/**
 * Chat types for the application
 */

export interface Chat {
  id: number
  title: string
  created_at: string
  updated_at: string
  user_id: number
  history_compression_enabled: boolean
  history_compression_message_limit: number | null
  compressed_history_summary: string | null
}

export interface ChatCreate {
  title: string
  history_compression_enabled?: boolean
  history_compression_message_limit?: number
}

export interface ChatUpdate {
  title?: string
  history_compression_enabled?: boolean
  history_compression_message_limit?: number | null
}

export interface Message {
  id: number
  chat_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  is_compressed?: boolean
}

export interface MessageCreate {
  chat_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
}
