export interface ForecastPoint {
  timestamp: string;
  actual_value?: number;
  predicted_value?: number;
  upper_bound?: number;
  lower_bound?: number;
}

export interface ForecastMetrics {
  mae: number;
  rmse: number;
  mape: number;
}

export interface ForecastResponse {
  id: string;
  name: string;
  points: ForecastPoint[];
  metrics: ForecastMetrics;
  explanation: string;
  forecast_start_date: string;
}
