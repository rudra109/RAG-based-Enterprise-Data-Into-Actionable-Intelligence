'use client';

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Paperclip, 
  ThumbsUp, 
  ThumbsDown, 
  Plus, 
  FileText, 
  ChevronDown, 
  Loader2,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Message, Corpus, RagDocument, Source } from '@/types/chat';
import { cn } from '@/lib/utils';
import { useStore } from '@/store/useStore';

export default function ChatInterface() {
  const { selectedWorkspace, addWorkspaceData, addRagDocuments, ragDocuments, ragFeedback, setRagFeedback } = useStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedCorpus, setSelectedCorpus] = useState<Corpus | null>(null);
  const [activeSource, setActiveSource] = useState<Source | null>(null);
  const corpora = useMemo<Corpus[]>(() => {
    if (selectedWorkspace === 'R&D Lab') {
      return [
        { id: 'rd-1', name: 'Experiment Notes', description: 'Model evaluation and benchmark docs' },
        { id: 'rd-2', name: 'Research Specs', description: 'R&D architecture and prompts' },
      ];
    }
    if (selectedWorkspace === 'Marketing Cloud') {
      return [
        { id: 'mk-1', name: 'Campaign Briefs', description: 'Campaign plans and creative specs' },
        { id: 'mk-2', name: 'Attribution Reports', description: 'Conversion and channel reports' },
      ];
    }
    if (selectedWorkspace !== 'Enterprise Workspace') {
      return [
        { id: 'custom-1', name: `${selectedWorkspace} Documents`, description: 'Uploaded workspace documents' },
      ];
    }
    return [
      { id: '1', name: 'Product Documentation', description: 'Internal product guides' },
      { id: '2', name: 'Legal Contracts', description: 'Signed vendor agreements' },
      { id: '3', name: 'Technical Specs', description: 'System architecture docs' },
    ];
  }, [selectedWorkspace]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const activeSelectedCorpus = corpora.some((corpus) => corpus.id === selectedCorpus?.id)
    ? selectedCorpus
    : null;
  const activeCorpus = activeSelectedCorpus || corpora[0] || null;
  const workspaceDocuments = ragDocuments[selectedWorkspace] || [];
  const activeDocuments = activeCorpus
    ? workspaceDocuments.filter((document) => document.corpusId === activeCorpus.id)
    : workspaceDocuments;

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      sources: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const response = await fetch('/v1/rag/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: input, 
          corpusId: activeCorpus?.id,
          workspace: selectedWorkspace,
          documents: workspaceDocuments,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        }),
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let pendingText = '';
      let sourcesLoaded = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        let chunk = decoder.decode(value);

        if (!sourcesLoaded) {
          pendingText += chunk;
          const newlineIndex = pendingText.indexOf('\n');

          if (newlineIndex === -1) {
            continue;
          }

          const metadataLine = pendingText.slice(0, newlineIndex).trim();
          chunk = pendingText.slice(newlineIndex + 1);
          pendingText = '';

          try {
            const data = JSON.parse(metadataLine);
            if (data.sources) {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId ? { ...msg, sources: data.sources } : msg
                )
              );
            }
            sourcesLoaded = true;
          } catch {
            chunk = `${metadataLine}\n${chunk}`;
            sourcesLoaded = true;
          }
        }

        fullContent += chunk;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId ? { ...msg, content: fullContent } : msg
          )
        );
      }
    } catch (error) {
      toast.error('Failed to get response from AI');
      console.error('Chat error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId 
            ? { ...msg, content: 'Sorry, I encountered an error. Please try again.' } 
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    const formData = new FormData();
    fileArray.forEach((file) => {
      formData.append('files', file);
    });
    
    if (activeCorpus) {
      formData.append('corpusId', activeCorpus.id);
    }
    formData.append('workspace', selectedWorkspace);

    try {
      const uploadedDocuments: RagDocument[] = await Promise.all(fileArray.map(async (file) => {
        let content = '';
        try {
          content = await file.text();
        } catch {
          content = `${file.name} could not be read as text in the browser.`;
        }

        return {
          id: `doc-${Date.now()}-${file.name}`,
          workspace: selectedWorkspace,
          corpusId: activeCorpus?.id || 'default',
          corpusName: activeCorpus?.name || `${selectedWorkspace} Documents`,
          name: file.name,
          type: file.type || 'text/plain',
          size: file.size,
          content,
          uploadedAt: new Date().toISOString(),
        };
      }));

      const response = await fetch('/v1/rag/ingest', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        addRagDocuments(selectedWorkspace, uploadedDocuments);
        toast.success(`Successfully uploaded ${files.length} document(s)`);
        uploadedDocuments.forEach((file) => {
          addWorkspaceData(selectedWorkspace, {
            name: file.name,
            type: 'Document Set',
            records: Math.max(1, file.content.split(/\s+/).filter(Boolean).length),
          });
        });
        console.log('Upload successful');
      } else {
        toast.error('Failed to upload documents');
        throw new Error('Upload failed');
      }
    } catch (error) {
      toast.error('An error occurred during upload');
      console.error('Upload error:', error);
    }
  };

  const handleFeedback = (messageId: string, type: 'up' | 'down') => {
    const nextFeedback = ragFeedback[messageId] === type ? null : type;
    setRagFeedback(messageId, nextFeedback);
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, feedback: nextFeedback } : msg
      )
    );
    fetch(`/v1/rag/feedback/${messageId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: nextFeedback }),
    }).catch(console.error);
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#020617] text-slate-200">
      {/* Header / Corpus Selector */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#020617]/50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-lg font-semibold text-white">RAG Intelligence</h1>
          <span className="rounded-full border border-slate-800 bg-slate-950 px-2 py-1 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            {selectedWorkspace}
          </span>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex items-center justify-center rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-all gap-2 shadow-sm focus:ring-2 focus:ring-indigo-500/20 outline-none">
            {activeCorpus ? activeCorpus.name : 'Select Corpus'}
            <ChevronDown className="w-4 h-4 opacity-50" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 bg-slate-900 border-slate-800 text-slate-300">
            {corpora.map((corpus) => (
              <DropdownMenuItem 
                key={corpus.id} 
                onClick={() => setSelectedCorpus(corpus)}
                className="hover:bg-slate-800 focus:bg-slate-800 cursor-pointer"
              >
                <div>
                  <div className="font-medium">{corpus.name}</div>
                  <div className="text-xs text-slate-500">{corpus.description}</div>
                </div>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Messages Area */}
      <ScrollArea className="min-h-0 flex-1 bg-[#020617] px-4 lg:px-8" ref={scrollRef}>
        <div className="max-w-4xl mx-auto py-8 space-y-8">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in slide-in-from-bottom-4 duration-700">
              <div 
                className="w-16 h-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-6 border border-indigo-500/20 cursor-pointer hover:bg-indigo-500/20 transition-all active:scale-95"
                onClick={() => fileInputRef.current?.click()}
              >
                <Plus className="w-8 h-8 text-indigo-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">How can I help you today?</h2>
              <p className="text-slate-400 max-w-sm">
                Upload documents into {activeCorpus?.name || selectedWorkspace}, then ask questions about their actual contents.
              </p>
              <p className="mt-3 max-w-md text-xs text-slate-600">
                Current corpus: {activeCorpus?.name || 'None'} - {activeDocuments.length} indexed document(s)
              </p>
            </div>
          )}

          {messages.map((message) => {
            const currentFeedback = message.role === 'assistant' ? (ragFeedback[message.id] || message.feedback) : message.feedback;
            return (
            <div
              key={message.id} 
              className={cn(
                "flex gap-4 group animate-in fade-in duration-300",
                message.role === 'user' ? "flex-row-reverse" : "flex-row"
              )}
            >
              <Avatar className="w-8 h-8 border border-slate-800 shrink-0">
                <AvatarImage src={message.role === 'user' ? '/user-avatar.png' : '/ai-avatar.png'} />
                <AvatarFallback className={message.role === 'user' ? "bg-slate-800" : "bg-indigo-600"}>
                  {message.role === 'user' ? 'U' : 'AI'}
                </AvatarFallback>
              </Avatar>

              <div className={cn(
                "flex flex-col gap-2 max-w-[85%]",
                message.role === 'user' ? "items-end" : "items-start"
              )}>
                <div className={cn(
                  "px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap",
                  message.role === 'user' 
                    ? "bg-indigo-600 text-white rounded-tr-none" 
                    : "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none"
                )}>
                  {message.content || (isLoading && message.role === 'assistant' && (
                    <div className="flex gap-1 py-1">
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></div>
                    </div>
                  ))}
                </div>

                {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1">
                    {message.sources.map((source, idx) => (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => setActiveSource(source)}
                        className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-950 border border-slate-800 text-[11px] text-slate-400 hover:text-slate-300 hover:border-slate-700 transition-all cursor-pointer"
                      >
                        <FileText className="w-3 h-3" />
                        <span>{source.name}</span>
                        {source.page && <span className="text-slate-600">- {source.page}</span>}
                      </button>
                    ))}
                  </div>
                )}

                {message.role === 'assistant' && message.content && (
                  <div className="flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className={cn("w-7 h-7 hover:bg-slate-800 rounded-lg", currentFeedback === 'up' && "text-indigo-400")}
                      onClick={() => handleFeedback(message.id, 'up')}
                      aria-pressed={currentFeedback === 'up'}
                      title="Helpful"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className={cn("w-7 h-7 hover:bg-slate-800 rounded-lg", currentFeedback === 'down' && "text-red-400")}
                      onClick={() => handleFeedback(message.id, 'down')}
                      aria-pressed={currentFeedback === 'down'}
                      title="Not helpful"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Input Area / Drag & Drop Zone */}
      <div 
        className={cn(
          "px-4 pb-6 pt-2 max-w-4xl mx-auto w-full relative transition-all duration-300",
          isDragging && "scale-[1.02]"
        )}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFileUpload(e.dataTransfer.files);
        }}
      >
        {isDragging && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-indigo-600/10 backdrop-blur-sm border-2 border-dashed border-indigo-500 rounded-3xl animate-in fade-in zoom-in duration-200">
            <Plus className="w-12 h-12 text-indigo-500 mb-2 animate-bounce" />
            <p className="text-lg font-semibold text-indigo-400">Drop to upload to {activeCorpus?.name || 'corpus'}</p>
          </div>
        )}

        <form 
          onSubmit={handleSend}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-2 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500 transition-all shadow-xl"
        >
          <div className="flex items-end gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 text-slate-400 hover:text-white hover:bg-slate-800 shrink-0"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="w-5 h-5" />
            </Button>
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              multiple 
              onChange={(e) => handleFileUpload(e.target.files)}
            />
            
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask a question..."
              className="w-full bg-transparent border-none focus:ring-0 text-slate-200 placeholder:text-slate-600 py-2 resize-none max-h-40 scrollbar-hide"
            />

            <Button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="h-10 w-10 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shrink-0 transition-transform active:scale-90"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </Button>
          </div>
        </form>
        
        <p className="text-[10px] text-slate-600 mt-3 text-center uppercase tracking-widest font-medium">
          Powered by NEXUS Intelligence - {selectedWorkspace} - {activeCorpus?.name || 'No Corpus Selected'} - {activeDocuments.length} document(s) indexed
        </p>
      </div>

      {activeSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6">
          <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white">{activeSource.name}</h2>
                <p className="text-xs text-slate-500">{activeSource.page || 'Retrieved source evidence'}</p>
              </div>
              <button
                type="button"
                onClick={() => setActiveSource(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-white"
                aria-label="Close source"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[50vh] overflow-y-auto rounded-xl border border-slate-800 bg-[#020617] p-4 text-sm leading-relaxed text-slate-300">
              {activeSource.excerpt || 'No excerpt was returned for this source.'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
