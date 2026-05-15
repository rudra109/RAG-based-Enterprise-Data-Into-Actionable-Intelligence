export type AnomalySeverity = 'critical' | 'warning' | 'info';

export interface Anomaly {
  id: string;
  metricName: string;
  timestamp: string;
  value: number;
  expectedValue: number;
  score: number; // 0 to 1
  severity: AnomalySeverity;
  isAcknowledged: boolean;
  description?: string;
}

export interface MetricPoint {
  timestamp: string;
  value: number;
  isAnomaly: boolean;
  anomalyId?: string;
}

export interface AnomalySummary {
  total: number;
  critical: number;
  unacknowledged: number;
  avgScore: number;
}
