import { RagDocument, Source } from '@/types/chat';

type ChatRequest = {
  query: string;
  workspace?: string;
  corpusId?: string;
  documents?: RagDocument[];
};

type RankedChunk = {
  document: RagDocument;
  text: string;
  score: number;
  matchedTerms: Set<string>;
  chunkIndex: number;
};

type RankedDocument = {
  document: RagDocument;
  chunks: RankedChunk[];
  score: number;
  matchedTerms: Set<string>;
};

const STOP_WORDS = new Set([
  'about', 'after', 'again', 'also', 'and', 'any', 'are', 'can', 'did', 'does',
  'for', 'from', 'have', 'how', 'into', 'like', 'many', 'please', 'should',
  'that', 'the', 'their', 'them', 'there', 'this', 'tell', 'was', 'what',
  'when', 'where', 'which', 'with', 'your',
]);

const SYNONYMS: Record<string, string> = {
  cleaned: 'clean',
  cleaning: 'clean',
  cleans: 'clean',
  columns: 'column',
  datasets: 'dataset',
  documents: 'document',
  emails: 'email',
  files: 'file',
  funcs: 'function',
  functions: 'function',
  latencies: 'latency',
  owns: 'owner',
  owned: 'owner',
  owner: 'owner',
  targets: 'target',
};

function normalizeToken(word: string) {
  const direct = SYNONYMS[word];
  if (direct) return direct;

  if (word.endsWith('ies') && word.length > 4) return `${word.slice(0, -3)}y`;
  if (word.endsWith('ing') && word.length > 5) return word.slice(0, -3);
  if (word.endsWith('ed') && word.length > 4) return word.slice(0, -2);
  if (word.endsWith('s') && word.length > 3) return word.slice(0, -1);

  return word;
}

function tokenize(value: string) {
  return value
    .toLowerCase()
    .replace(/[_-]/g, ' ')
    .replace(/[^a-z0-9\s.]/g, ' ')
    .split(/\s+/)
    .map((word) => word.trim().replace(/^\.+|\.+$/g, ''))
    .filter((word) => word.length >= 2 && !STOP_WORDS.has(word))
    .map(normalizeToken)
    .filter((word) => word.length >= 2 && !STOP_WORDS.has(word));
}

function splitSentences(value: string) {
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (!normalized) return [];

  return normalized.match(/[^.!?\n]+[.!?]?/g)?.map((sentence) => sentence.trim()).filter(Boolean) || [normalized];
}

function chunkDocument(document: RagDocument) {
  const sentences = splitSentences(document.content);
  const chunks: string[] = [];
  let current = '';

  for (const sentence of sentences) {
    if ((current + sentence).length > 650 && current) {
      chunks.push(current.trim());
      current = '';
    }
    current += `${sentence} `;
  }

  if (current.trim()) chunks.push(current.trim());
  return chunks;
}

function scoreText(text: string, queryTerms: string[]) {
  const textTerms = tokenize(text);
  const textTermSet = new Set(textTerms);
  const matchedTerms = new Set(queryTerms.filter((term) => textTermSet.has(term) || text.toLowerCase().includes(term)));
  const exactMatches = textTerms.filter((term) => matchedTerms.has(term)).length;
  const phraseBonus = queryTerms.length > 1 && text.toLowerCase().includes(queryTerms.join(' ')) ? 8 : 0;

  return {
    matchedTerms,
    score: exactMatches * 3 + matchedTerms.size * 6 + phraseBonus,
  };
}

function nameMatchScore(query: string, document: RagDocument) {
  const queryLower = query.toLowerCase();
  const nameLower = document.name.toLowerCase();
  const baseName = nameLower.replace(/\.[^.]+$/, '');
  const readableBaseName = baseName.replace(/[_-]/g, ' ');
  const singularBaseName = baseName.endsWith('s') ? baseName.slice(0, -1) : baseName;

  if (queryLower.includes(nameLower)) return 35;
  if (queryLower.includes(baseName)) return 30;
  if (queryLower.includes(readableBaseName)) return 25;
  if (queryLower.includes(singularBaseName)) return 22;

  const queryTerms = new Set(tokenize(query));
  const fileTerms = tokenize(document.name);
  return fileTerms.filter((term) => queryTerms.has(term)).length * 8;
}

function rankDocuments(query: string, documents: RagDocument[]): RankedDocument[] {
  const queryTerms = tokenize(query);

  return documents
    .map((document) => {
      const chunks = chunkDocument(document)
        .map((text, chunkIndex) => {
          const scored = scoreText(text, queryTerms);
          return {
            document,
            text,
            chunkIndex,
            score: scored.score,
            matchedTerms: scored.matchedTerms,
          };
        })
        .sort((a, b) => b.score - a.score);

      const matchedTerms = new Set<string>();
      chunks.slice(0, 3).forEach((chunk) => chunk.matchedTerms.forEach((term) => matchedTerms.add(term)));

      const bestChunkScore = chunks[0]?.score || 0;
      const nextChunkScore = chunks[1]?.score || 0;
      const score = bestChunkScore + nextChunkScore * 0.35 + matchedTerms.size * 5 + nameMatchScore(query, document);

      return { document, chunks, score, matchedTerms };
    })
    .sort((a, b) => b.score - a.score);
}

function findMentionedDocument(query: string, documents: RagDocument[]) {
  const queryLower = query.toLowerCase();

  return documents.find((document) => {
    const nameLower = document.name.toLowerCase();
    const baseName = nameLower.replace(/\.[^.]+$/, '');
    const readableBaseName = baseName.replace(/[_-]/g, ' ');
    const singularBaseName = baseName.endsWith('s') ? baseName.slice(0, -1) : baseName;

    return (
      queryLower.includes(nameLower) ||
      queryLower.includes(baseName) ||
      queryLower.includes(readableBaseName) ||
      queryLower.includes(singularBaseName)
    );
  });
}

function queryMentionsFileName(query: string) {
  return /\b[a-z0-9_-]+\.(py|ts|tsx|js|jsx|json|csv|md|txt)\b/i.test(query);
}

function isFunctionCountQuestion(query: string) {
  return /\b(how many|count|number of)\b/i.test(query) && /\b(function|functions|def|methods)\b/i.test(query);
}

function isDatabaseInventoryQuestion(query: string) {
  return /\b(my\s+)?database\b/i.test(query) && /\b(how many|count|number of|total)\b/i.test(query);
}

function getFunctionNames(content: string) {
  const names: string[] = [];
  const patterns = [
    /^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/gm,
    /^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(/gm,
    /^\s*(?:export\s+)?const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\(/gm,
  ];

  for (const pattern of patterns) {
    for (const match of content.matchAll(pattern)) {
      if (match[1] && !names.includes(match[1])) names.push(match[1]);
    }
  }

  return names;
}

function buildSources(chunks: RankedChunk[]) {
  return chunks.map((chunk) => ({
    id: chunk.document.id,
    name: chunk.document.name,
    page: `chunk ${chunk.chunkIndex + 1}`,
    excerpt: chunk.text,
  }));
}

function formatAnswer(answer: string, evidence: string, source?: string) {
  return [
    `Answer:\n${answer}`,
    `Evidence:\n${evidence}`,
    source ? `Source:\n${source}` : undefined,
  ].filter(Boolean).join('\n\n');
}

function buildNoDirectAnswer(query: string, workspace: string, extraGuidance?: string) {
  return {
    answer: formatAnswer(
      `I do not know from the indexed ${workspace} documents.`,
      `I could not find a direct answer for "${query}" in the selected corpus.${extraGuidance ? ` ${extraGuidance}` : ''}`,
    ),
    sources: [] as Source[],
  };
}

function buildFunctionCountAnswer(query: string, workspace: string, documents: RagDocument[]) {
  const mentionedDocument = findMentionedDocument(query, documents);

  if (!mentionedDocument) {
    return buildNoDirectAnswer(
      query,
      workspace,
      queryMentionsFileName(query)
        ? 'That file is not uploaded or indexed in this workspace yet.'
        : 'Mention the exact uploaded file name if you want me to count functions in a code file.',
    );
  }

  const functionNames = getFunctionNames(mentionedDocument.content);
  const shownNames = functionNames.slice(0, 12).join(', ');
  const remaining = Math.max(functionNames.length - 12, 0);
  const nameEvidence = functionNames.length > 0
    ? `I counted function definitions in ${mentionedDocument.name}. Detected names: ${shownNames}${remaining ? `, and ${remaining} more` : ''}.`
    : `I scanned ${mentionedDocument.name}, but did not find Python or JavaScript function definitions.`;

  return {
    answer: formatAnswer(
      `${mentionedDocument.name} contains ${functionNames.length} function definition${functionNames.length === 1 ? '' : 's'} in the indexed upload.`,
      nameEvidence,
      `${mentionedDocument.name}`,
    ),
    sources: [{
      id: mentionedDocument.id,
      name: mentionedDocument.name,
      page: 'function scan',
      excerpt: mentionedDocument.content.slice(0, 1200),
    }],
  };
}

function buildCodeOverviewAnswer(query: string, workspace: string, documents: RagDocument[]) {
  const mentionedDocument = findMentionedDocument(query, documents);
  if (!mentionedDocument || !/\.(py|ts|tsx|js|jsx)$/i.test(mentionedDocument.name)) return null;

  const asksWhatItIs = /\bwhat is\b/i.test(query);
  const asksFunctions = /\b(function|functions|def|methods)\b/i.test(query);
  if (!asksWhatItIs || !asksFunctions) return null;

  const functionNames = getFunctionNames(mentionedDocument.content);
  const imports = Array.from(mentionedDocument.content.matchAll(/^\s*(?:from\s+[\w.]+\s+import|import\s+[\w.,\s]+)/gm))
    .map((match) => match[0].trim())
    .slice(0, 4);

  return {
    answer: formatAnswer(
      `${mentionedDocument.name} is a source-code file in the indexed ${workspace} documents. It contains ${functionNames.length} function definition${functionNames.length === 1 ? '' : 's'}.`,
      `The file imports or references ${imports.length ? imports.join('; ') : 'code-level dependencies'} and includes function definitions such as ${functionNames.slice(0, 10).join(', ') || 'none found'}.`,
      `${mentionedDocument.name}`,
    ),
    sources: [{
      id: mentionedDocument.id,
      name: mentionedDocument.name,
      page: 'function scan',
      excerpt: mentionedDocument.content.slice(0, 1200),
    }],
  };
}

function pickAnswerSentences(query: string, chunks: RankedChunk[]) {
  const queryTerms = tokenize(query);
  const rankedSentences = chunks
    .flatMap((chunk) =>
      splitSentences(chunk.text).map((sentence) => {
        const scored = scoreText(sentence, queryTerms);
        return { sentence, score: scored.score, matchedTerms: scored.matchedTerms };
      })
    )
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score);

  const selected: string[] = [];
  const coveredTerms = new Set<string>();

  for (const item of rankedSentences) {
    if (selected.length >= 3) break;
    const addsNewTerm = Array.from(item.matchedTerms).some((term) => !coveredTerms.has(term));
    if (addsNewTerm || selected.length === 0) {
      selected.push(item.sentence);
      item.matchedTerms.forEach((term) => coveredTerms.add(term));
    }
  }

  return selected.join(' ');
}

function buildRetrievedAnswer(query: string, workspace: string, documents: RagDocument[]) {
  if (documents.length === 0) {
    return {
      answer: formatAnswer(
        `I do not have any indexed documents for ${workspace} yet.`,
        'Upload a text, CSV, JSON, markdown, or code file first. Then ask a question about what is inside that uploaded file.',
      ),
      sources: [] as Source[],
    };
  }

  const rankedDocuments = rankDocuments(query, documents);
  const bestDocument = rankedDocuments[0];
  const queryTerms = tokenize(query);
  const requiredTermMatches = Math.min(2, Math.max(1, queryTerms.length));

  if (!bestDocument || bestDocument.score < 12 || bestDocument.matchedTerms.size < requiredTermMatches) {
    return buildNoDirectAnswer(query, workspace);
  }

  const relevantChunks = bestDocument.chunks
    .filter((chunk) => chunk.score > 0 && chunk.matchedTerms.size > 0)
    .slice(0, 2);

  const answerText = pickAnswerSentences(query, relevantChunks) || relevantChunks[0]?.text;

  if (!answerText) {
    return buildNoDirectAnswer(query, workspace);
  }

  return {
    answer: formatAnswer(
      answerText,
      `I used the best matching document only, so unrelated uploads are not mixed into this answer.`,
      `${bestDocument.document.name}`,
    ),
    sources: buildSources(relevantChunks),
  };
}

function buildAnswer(query: string, workspace: string, documents: RagDocument[]) {
  const trimmedQuery = query.trim();

  if (documents.length === 0) {
    return buildRetrievedAnswer(trimmedQuery, workspace, documents);
  }

  if (isDatabaseInventoryQuestion(trimmedQuery)) {
    return {
      answer: formatAnswer(
        'I cannot count records in your real database from uploaded code files.',
        'The indexed documents describe code or text content only. To answer database-count questions, upload a database export such as CSV or JSON that contains those records, or connect the app to the actual database API.',
      ),
      sources: [] as Source[],
    };
  }

  if (isFunctionCountQuestion(trimmedQuery)) {
    return buildFunctionCountAnswer(trimmedQuery, workspace, documents);
  }

  const codeOverview = buildCodeOverviewAnswer(trimmedQuery, workspace, documents);
  if (codeOverview) return codeOverview;

  return buildRetrievedAnswer(trimmedQuery, workspace, documents);
}

export async function POST(req: Request) {
  const { query, workspace = 'Enterprise Workspace', corpusId, documents = [] } = await req.json() as ChatRequest;
  const scopedDocuments = documents.filter((document) => (
    document.workspace === workspace && (!corpusId || document.corpusId === corpusId)
  ));
  const { answer, sources } = buildAnswer(query, workspace, scopedDocuments);

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode(`${JSON.stringify({ sources })}\n`));

      controller.enqueue(encoder.encode(answer));

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}
