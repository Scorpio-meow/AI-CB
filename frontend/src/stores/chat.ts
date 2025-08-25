import { create } from 'zustand'

export type Role = 'user' | 'assistant'
export interface ChatMsg {
  id: number
  role: Role
  text: string
}

interface ChatState {
  msgs: ChatMsg[]
  add: (m: ChatMsg) => void
  // Update text of a message by id; useful for streaming
  updateText: (id: number, updater: (prev: string) => string) => void
  clear: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  msgs: [],
  add: (m) => set((s) => ({ msgs: [...s.msgs, m] })),
  updateText: (id, updater) =>
    set((s) => ({
      msgs: s.msgs.map((m) => (m.id === id ? { ...m, text: updater(m.text) } : m)),
    })),
  clear: () => set({ msgs: [] }),
}))
