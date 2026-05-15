import { create } from 'zustand';

interface AppState {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  selectedWorkspace: string;
  setSelectedWorkspace: (workspace: string) => void;
}

export const useStore = create<AppState>((set) => ({
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  selectedWorkspace: 'Enterprise Workspace',
  setSelectedWorkspace: (workspace) => set({ selectedWorkspace: workspace }),
}));
