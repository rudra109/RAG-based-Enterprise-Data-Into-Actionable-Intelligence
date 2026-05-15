'use client';

import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Paperclip, 
  ThumbsUp, 
  ThumbsDown, 
  Plus, 
  FileText, 
  ChevronDown, 
  Loader2,
  Trash2,
  CheckCircle2,
  AlertCircle,
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
import { Message, Source, Corpus } from '@/types/chat';
import { cn } from '@/lib/utils';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedCorpus, setSelectedCorpus] = useState<Corpus | null>(null);
  const [corpora] = useState<Corpus[]>([
    { id: '1', name: 'Product Documentation', description: 'Internal product guides' },
    { id: '2', name: 'Legal Contracts', description: 'Signed vendor agreements' },
    { id: '3', name: 'Technical Specs', description: 'System architecture docs' },
  ]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

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
          corpusId: selectedCorpus?.id,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        }),
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        // Assuming chunk might contain multiple events in SSE format
        // For simplicity, we'll handle plain text or simple JSON chunks
        try {
          // Attempt to parse as JSON if it looks like it (e.g. metadata)
          if (chunk.startsWith('{')) {
            const data = JSON.parse(chunk);
            if (data.sources) {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId ? { ...msg, sources: data.sources } : msg
                )
              );
              continue;
            }
          }
        } catch (e) {
          // Not JSON, treat as text chunk
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

    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append('files', file);
    });
    
    if (selectedCorpus) {
      formData.append('corpusId', selectedCorpus.id);
    }

    try {
      const response = await fetch('/v1/rag/ingest', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        toast.success(`Successfully uploaded ${files.length} document(s)`);
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
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, feedback: msg.feedback === type ? null : type } : msg
      )
    );
    // Call API in background
    fetch(`/v1/rag/feedback/${messageId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type }),
    }).catch(console.error);
  };

  return (
    <div className="flex flex-col h-full bg-[#020617] text-slate-200">
      {/* Header / Corpus Selector */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#020617]/50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-lg font-semibold text-white">RAG Intelligence</h1>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger className="inline-flex items-center justify-center rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-all gap-2 shadow-sm focus:ring-2 focus:ring-indigo-500/20 outline-none">
            {selectedCorpus ? selectedCorpus.name : 'Select Corpus'}
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
      <ScrollArea className="flex-1 px-4 lg:px-8" ref={scrollRef}>
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
                Ask questions about your documents, technical specs, or internal guides.
              </p>
            </div>
          )}

          {messages.map((message) => (
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
                  "px-4 py-3 rounded-2xl text-sm leading-relaxed",
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
                      <div 
                        key={idx} 
                        className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-950 border border-slate-800 text-[11px] text-slate-400 hover:text-slate-300 hover:border-slate-700 transition-all cursor-pointer"
                      >
                        <FileText className="w-3 h-3" />
                        <span>{source.name}</span>
                        {source.page && <span className="text-slate-600">• p.{source.page}</span>}
                      </div>
                    ))}
                  </div>
                )}

                {message.role === 'assistant' && message.content && (
                  <div className="flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className={cn("w-7 h-7 hover:bg-slate-800 rounded-lg", message.feedback === 'up' && "text-indigo-400")}
                      onClick={() => handleFeedback(message.id, 'up')}
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className={cn("w-7 h-7 hover:bg-slate-800 rounded-lg", message.feedback === 'down' && "text-red-400")}
                      onClick={() => handleFeedback(message.id, 'down')}
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
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
            <p className="text-lg font-semibold text-indigo-400">Drop to upload to {selectedCorpus?.name || 'corpus'}</p>
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
          Powered by NEXUS Intelligence • {selectedCorpus?.name || 'No Corpus Selected'}
        </p>
      </div>
    </div>
  );
}
