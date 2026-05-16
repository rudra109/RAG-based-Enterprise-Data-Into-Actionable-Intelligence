export type ChartType = 'bar' | 'line' | 'pie';

export interface QueryResult {
  id: string;
  query: string;
  workspace: string;
  sql: string;
  explanation: string;
  chartSuggestion: ChartType;
  data: any[];
  timestamp: number;
}

export interface HistoryItem {
  id: string;
  query: string;
  timestamp: number;
}
