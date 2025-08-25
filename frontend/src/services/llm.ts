import { api } from './api'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export async function generate(messages: ChatMessage[], context?: string): Promise<string> {
  const { data } = await api.post('/llm/generate', { messages, context })
  return data.text as string
}
