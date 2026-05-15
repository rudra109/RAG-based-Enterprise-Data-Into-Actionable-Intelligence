import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const { query } = await req.json();
  
  await new Promise(resolve => setTimeout(resolve, 1200));

  return NextResponse.json({
    sql: `SELECT region, SUM(revenue) as total_revenue \nFROM sales_data \nWHERE date >= '2026-01-01' \nGROUP BY region \nORDER BY total_revenue DESC;`,
    explanation: `I've aggregated the total revenue across all geographical sectors. North America is currently leading with a 15% increase compared to last month, primarily driven by enterprise subscription renewals.`,
    chart_suggestion: 'bar',
    data: [
      { region: 'North America', total_revenue: 450000 },
      { region: 'EMEA', total_revenue: 320000 },
      { region: 'APAC', total_revenue: 280000 },
      { region: 'LATAM', total_revenue: 150000 },
    ]
  });
}
