import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { QueryResult } from '@/types/agent';

interface AgentState {
  history: QueryResult[];
  addHistoryItem: (item: QueryResult) => void;
  clearHistory: () => void;
}

export const useAgentStore = create<AgentState>()(
  persist(
    (set) => ({
      history: [],
      addHistoryItem: (item) => set((state) => ({
        history: [item, ...state.history].slice(0, 10)
      })),
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: 'agent-storage',
    }
  )
);
