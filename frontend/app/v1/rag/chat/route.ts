import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const { query } = await req.json();
  
  // Create a readable stream to simulate SSE
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      
      // Send sources first
      const sources = JSON.stringify({
        sources: [
          { name: 'Product_Specs_v2.pdf', page: 12 },
          { name: 'Architecture_Diagram.png', page: 1 }
        ]
      });
      controller.enqueue(encoder.encode(sources));
      
      // Simulate typing delay and stream words
      const responseText = `Based on the documents provided, ${query} is addressed in section 4.2. The system utilizes a distributed vector store with HNSW indexing to ensure sub-second retrieval latency for large-scale datasets.`;
      const words = responseText.split(' ');
      
      for (const word of words) {
        await new Promise(resolve => setTimeout(resolve, 50));
        controller.enqueue(encoder.encode(word + ' '));
      }
      
      controller.close();
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}
