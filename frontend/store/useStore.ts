import { create } from 'zustand';
import { RagDocument } from '@/types/chat';

interface AppState {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  workspaces: Workspace[];
  workspaceData: Record<string, WorkspaceData>;
  ragDocuments: Record<string, RagDocument[]>;
  ragFeedback: Record<string, 'up' | 'down'>;
  selectedWorkspace: string;
  setSelectedWorkspace: (workspace: string) => void;
  addWorkspace: (workspace: Workspace) => void;
  addWorkspaceData: (workspace: string, input: AddWorkspaceDataInput) => void;
  addRagDocuments: (workspace: string, documents: RagDocument[]) => void;
  setRagFeedback: (messageId: string, feedback: 'up' | 'down' | null) => void;
  hydrateWorkspaceState: () => void;
}

const DEFAULT_WORKSPACE = 'Enterprise Workspace';
export interface Workspace {
  id: string;
  name: string;
  type: string;
}

export interface WorkspaceData {
  dataPoints: number;
  activeQueries: number;
  activeUsers: number;
  anomalies: number;
  sources: Array<{
    id: string;
    name: string;
    type: string;
    records: number;
    addedAt: string;
  }>;
}

export interface AddWorkspaceDataInput {
  name: string;
  type: string;
  records: number;
}

const DEFAULT_WORKSPACES: Workspace[] = [
  { id: "1", name: "Enterprise Workspace", type: "Main" },
  { id: "2", name: "R&D Lab", type: "Department" },
  { id: "3", name: "Marketing Cloud", type: "Team" },
];

function createEmptyWorkspaceData(): WorkspaceData {
  return {
    dataPoints: 0,
    activeQueries: 0,
    activeUsers: 1,
    anomalies: 0,
    sources: [],
  };
}

function persistWorkspaceState(
  workspaces: Workspace[],
  selectedWorkspace: string,
  workspaceData: Record<string, WorkspaceData>,
  ragDocuments: Record<string, RagDocument[]> = {},
  ragFeedback: Record<string, 'up' | 'down'> = {},
) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('enterpriseiq.workspaces', JSON.stringify(workspaces));
  window.localStorage.setItem('enterpriseiq.workspace', selectedWorkspace);
  window.localStorage.setItem('enterpriseiq.workspaceData', JSON.stringify(workspaceData));
  window.localStorage.setItem('enterpriseiq.ragDocuments', JSON.stringify(ragDocuments));
  window.localStorage.setItem('enterpriseiq.ragFeedback', JSON.stringify(ragFeedback));
}

export const useStore = create<AppState>((set) => ({
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  workspaces: DEFAULT_WORKSPACES,
  workspaceData: {},
  ragDocuments: {},
  ragFeedback: {},
  selectedWorkspace: DEFAULT_WORKSPACE,
  setSelectedWorkspace: (workspace) => set((state) => {
    persistWorkspaceState(state.workspaces, workspace, state.workspaceData, state.ragDocuments, state.ragFeedback);
    return { selectedWorkspace: workspace };
  }),
  addWorkspace: (workspace) => set((state) => {
    const exists = state.workspaces.some((item) => item.name.toLowerCase() === workspace.name.toLowerCase());
    const workspaces = exists ? state.workspaces : [...state.workspaces, workspace];
    const workspaceData = {
      ...state.workspaceData,
      [workspace.name]: state.workspaceData[workspace.name] || createEmptyWorkspaceData(),
    };
    persistWorkspaceState(workspaces, workspace.name, workspaceData, state.ragDocuments, state.ragFeedback);
    return { workspaces, workspaceData, selectedWorkspace: workspace.name };
  }),
  addWorkspaceData: (workspace, input) => set((state) => {
    const current = state.workspaceData[workspace] || createEmptyWorkspaceData();
    const source = {
      id: `source-${Date.now()}`,
      name: input.name,
      type: input.type,
      records: input.records,
      addedAt: new Date().toISOString(),
    };
    const workspaceData = {
      ...state.workspaceData,
      [workspace]: {
        dataPoints: current.dataPoints + input.records,
        activeQueries: current.activeQueries + Math.max(1, Math.round(input.records / 1000)),
        activeUsers: current.activeUsers,
        anomalies: current.anomalies,
        sources: [source, ...current.sources].slice(0, 8),
      },
    };

    persistWorkspaceState(state.workspaces, state.selectedWorkspace, workspaceData, state.ragDocuments, state.ragFeedback);
    return { workspaceData };
  }),
  addRagDocuments: (workspace, documents) => set((state) => {
    const current = state.ragDocuments[workspace] || [];
    const ragDocuments = {
      ...state.ragDocuments,
      [workspace]: [...documents, ...current].slice(0, 40),
    };

    persistWorkspaceState(state.workspaces, state.selectedWorkspace, state.workspaceData, ragDocuments, state.ragFeedback);
    return { ragDocuments };
  }),
  setRagFeedback: (messageId, feedback) => set((state) => {
    const ragFeedback = { ...state.ragFeedback };
    if (feedback) {
      ragFeedback[messageId] = feedback;
    } else {
      delete ragFeedback[messageId];
    }

    persistWorkspaceState(state.workspaces, state.selectedWorkspace, state.workspaceData, state.ragDocuments, ragFeedback);
    return { ragFeedback };
  }),
  hydrateWorkspaceState: () => {
    if (typeof window === 'undefined') return;

    const storedWorkspaces = window.localStorage.getItem('enterpriseiq.workspaces');
    const storedSelectedWorkspace = window.localStorage.getItem('enterpriseiq.workspace');
    const storedWorkspaceData = window.localStorage.getItem('enterpriseiq.workspaceData');
    const storedRagDocuments = window.localStorage.getItem('enterpriseiq.ragDocuments');
    const storedRagFeedback = window.localStorage.getItem('enterpriseiq.ragFeedback');
    let workspaces = DEFAULT_WORKSPACES;
    let workspaceData: Record<string, WorkspaceData> = {};
    let ragDocuments: Record<string, RagDocument[]> = {};
    let ragFeedback: Record<string, 'up' | 'down'> = {};

    if (storedWorkspaces) {
      try {
        const parsed = JSON.parse(storedWorkspaces) as Workspace[];
        if (Array.isArray(parsed) && parsed.every((item) => item.id && item.name && item.type)) {
          workspaces = parsed;
        }
      } catch {
        workspaces = DEFAULT_WORKSPACES;
      }
    }

    if (storedWorkspaceData) {
      try {
        const parsed = JSON.parse(storedWorkspaceData) as Record<string, WorkspaceData>;
        if (parsed && typeof parsed === 'object') {
          workspaceData = parsed;
        }
      } catch {
        workspaceData = {};
      }
    }

    if (storedRagDocuments) {
      try {
        const parsed = JSON.parse(storedRagDocuments) as Record<string, RagDocument[]>;
        if (parsed && typeof parsed === 'object') {
          ragDocuments = parsed;
        }
      } catch {
        ragDocuments = {};
      }
    }

    if (storedRagFeedback) {
      try {
        const parsed = JSON.parse(storedRagFeedback) as Record<string, 'up' | 'down'>;
        if (parsed && typeof parsed === 'object') {
          ragFeedback = parsed;
        }
      } catch {
        ragFeedback = {};
      }
    }

    const selectedWorkspace = storedSelectedWorkspace && workspaces.some((item) => item.name === storedSelectedWorkspace)
      ? storedSelectedWorkspace
      : DEFAULT_WORKSPACE;

    set({ workspaces, workspaceData, ragDocuments, ragFeedback, selectedWorkspace });
  },
}));
