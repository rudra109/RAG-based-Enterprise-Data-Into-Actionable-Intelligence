export interface Source {
  id?: string;
  name: string;
  page?: number | string;
  excerpt?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: number;
  feedback?: 'up' | 'down' | null;
}

export interface Corpus {
  id: string;
  name: string;
  description?: string;
}

export interface RagDocument {
  id: string;
  workspace: string;
  corpusId: string;
  corpusName: string;
  name: string;
  type: string;
  size: number;
  content: string;
  uploadedAt: string;
}
