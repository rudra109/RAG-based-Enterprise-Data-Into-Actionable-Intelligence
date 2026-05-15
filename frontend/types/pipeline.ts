export type PipelineStatus = 'running' | 'success' | 'failed' | 'scheduled' | 'idle';

export interface Pipeline {
  id: string;
  name: string;
  status: PipelineStatus;
  recordsProcessed: number;
  totalRecords: number;
  lastRun?: string;
  progress: number; // 0 to 100
}

export interface PipelineRun {
  id: string;
  pipelineId: string;
  startTime: string;
  endTime?: string;
  status: PipelineStatus;
  logs: LogEntry[];
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
  step?: string;
}
