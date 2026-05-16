import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  await req.json();
  
  // Simulate session creation
  const response = NextResponse.json({ success: true });
  
  // Set a mock session cookie
  response.cookies.set('session', 'mock-session-id', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 7, // 1 week
    path: '/',
  });
  
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ success: true });
  response.cookies.delete('session');
  return response;
}
