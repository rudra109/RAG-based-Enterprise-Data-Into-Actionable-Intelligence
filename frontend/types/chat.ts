export interface Source {
  name: string;
  page?: number | string;
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
