import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const { type } = await req.json();

  return NextResponse.json({
    success: true,
    feedback: type,
  });
}
