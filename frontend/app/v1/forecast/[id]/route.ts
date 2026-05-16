import { NextResponse } from 'next/server';

type WorkspaceForecastConfig = {
  base: number;
  amplitude: number;
  mae: number;
  rmse: number;
  mape: number;
  explanation: string;
};

const workspaceConfig: Record<string, WorkspaceForecastConfig> = {
  'Enterprise Workspace': {
    base: 100,
    amplitude: 20,
    mae: 4.2,
    rmse: 5.8,
    mape: 3.1,
    explanation: 'Based on seasonal trends and recent growth patterns, resource demand is expected to keep rising. The forecast changes with the selected time horizon, with wider confidence bands for longer periods.',
  },
  'R&D Lab': {
    base: 72,
    amplitude: 28,
    mae: 6.4,
    rmse: 8.2,
    mape: 5.9,
    explanation: 'R&D Lab demand is expected to spike around experiment batches. Forecast confidence is moderate because research workloads are bursty and tied to model evaluation cycles.',
  },
  'Marketing Cloud': {
    base: 130,
    amplitude: 16,
    mae: 3.8,
    rmse: 5.1,
    mape: 2.8,
    explanation: 'Marketing Cloud demand is projected to rise steadily during campaign windows, with paid search and lifecycle automation contributing the strongest growth signals.',
  },
};

function parseHorizon(value: string | null) {
  const days = Number.parseInt(value || '30d', 10);
  return Number.isFinite(days) && days > 0 ? days : 30;
}

function round(value: number, places = 1) {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

function buildCustomConfig(workspace: string, dataPoints: number, sourceCount: number): WorkspaceForecastConfig {
  if (dataPoints <= 0 || sourceCount <= 0) {
    return {
      base: 0,
      amplitude: 0,
      mae: 0,
      rmse: 0,
      mape: 0,
      explanation: `${workspace} does not have enough historical data for a confident forecast yet. Add data on the dashboard or upload documents so the forecast can build a baseline.`,
    };
  }

  const base = Math.max(12, Math.round(dataPoints / Math.max(sourceCount, 1) / 35));
  return {
    base,
    amplitude: Math.max(4, Math.round(base * 0.22)),
    mae: round(Math.max(1.2, base * 0.045)),
    rmse: round(Math.max(1.8, base * 0.062)),
    mape: round(Math.max(2.4, 8.2 - Math.min(sourceCount, 8) * 0.45)),
    explanation: `${workspace} forecast is based on ${dataPoints.toLocaleString()} records across ${sourceCount} connected source(s). Longer horizons use wider confidence bands because the prediction is less certain further out.`,
  };
}

export async function GET(req: Request) {
  const url = new URL(req.url);
  const workspace = url.searchParams.get('workspace') || 'Enterprise Workspace';
  const horizonDays = parseHorizon(url.searchParams.get('horizon'));
  const dataPoints = Number.parseInt(url.searchParams.get('dataPoints') || '0', 10);
  const sourceCount = Number.parseInt(url.searchParams.get('sources') || '0', 10);
  const configured = workspaceConfig[workspace];
  const config = configured || buildCustomConfig(workspace, dataPoints, sourceCount);
  const hasData = Boolean(configured || (dataPoints > 0 && sourceCount > 0));

  if (!hasData) {
    return NextResponse.json({
      id: url.pathname.split('/').pop(),
      name: `${workspace} Forecast`,
      points: [],
      forecast_start_date: new Date(Date.UTC(2026, 4, 15)).toISOString().split('T')[0],
      explanation: config.explanation,
      has_data: false,
      metrics: {
        mae: 0,
        rmse: 0,
        mape: 0,
      },
    });
  }

  const historyDays = Math.min(30, Math.max(14, Math.round(horizonDays / 3)));
  const forecastStep = horizonDays > 120 ? 6 : horizonDays > 60 ? 3 : horizonDays > 30 ? 2 : 1;
  const forecastPoints = Math.max(7, Math.ceil(horizonDays / forecastStep));
  const totalPoints = historyDays + forecastPoints;
  const startDate = new Date(Date.UTC(2026, 4, 15));
  const horizonFactor = 1 + horizonDays / 365;
  const confidenceWidth = Math.max(8, config.amplitude * (0.7 + horizonDays / 180));

  const points = Array.from({ length: totalPoints }).map((_, i) => {
    const isForecast = i >= historyDays;
    const forecastIndex = Math.max(0, i - historyDays);
    const daysFromStart = isForecast ? forecastIndex * forecastStep : i - historyDays;
    const date = new Date(startDate);
    date.setUTCDate(startDate.getUTCDate() + daysFromStart);

    const trend = isForecast ? forecastIndex * (0.18 * horizonFactor) : i * 0.08;
    const seasonal = Math.sin(i / 4.5) * config.amplitude;
    const weekly = Math.cos(i / 2.2) * (config.amplitude * 0.22);
    const baseline = config.base + trend + seasonal + weekly;
    const actual = isForecast ? null : round(baseline + (((i * 7) % 9) - 4));
    const predicted = round(baseline + (isForecast ? forecastIndex * 0.12 * horizonFactor : 0));

    return {
      timestamp: date.toISOString().split('T')[0],
      actual_value: actual,
      predicted_value: predicted,
      upper_bound: round(predicted + confidenceWidth + forecastIndex * 0.12),
      lower_bound: round(Math.max(0, predicted - confidenceWidth - forecastIndex * 0.12)),
    };
  });

  const metricFactor = 1 + horizonDays / 420;

  return NextResponse.json({
    id: url.pathname.split('/').pop(),
    name: `${workspace} Forecast`,
    points,
    forecast_start_date: startDate.toISOString().split('T')[0],
    explanation: `${config.explanation} Current horizon: ${horizonDays} days.`,
    has_data: true,
    metrics: {
      mae: round(config.mae * metricFactor),
      rmse: round(config.rmse * metricFactor),
      mape: round(config.mape * metricFactor),
    },
  });
}
