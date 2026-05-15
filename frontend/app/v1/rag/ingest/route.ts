import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const formData = await req.formData();
  const files = formData.getAll('files');
  
  console.log(`Mocking upload of ${files.length} files`);
  
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  return NextResponse.json({ 
    success: true, 
    message: `${files.length} files successfully ingested and indexed.` 
  });
}
