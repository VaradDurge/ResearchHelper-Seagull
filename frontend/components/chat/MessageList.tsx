/**
 * # MessageList Component
 * 
 * Displays the conversation history with ChatGPT-like styling.
 */
"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { User, Bot } from "lucide-react";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    paper_id: string;
    paper_title: string;
    page_number: number;
    chunk_index: number;
    text: string;
  }>;
  timestamp?: Date;
}

interface MessageListProps {
  messages: Message[];
  isLoading?: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-muted-foreground text-sm">
            Start a conversation with your papers
          </p>
          <p className="text-muted-foreground text-xs">
            Ask questions about the uploaded research papers
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 min-h-0">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex gap-4",
              message.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            {message.role === "assistant" && (
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
              </div>
            )}
            
            <div
              className={cn(
                "rounded-2xl px-4 py-3 max-w-[85%]",
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              )}
            >
              <p className="text-sm whitespace-pre-wrap break-words">
                {message.content}
              </p>
              
              {message.citations && message.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/50">
                  <p className="text-xs font-medium mb-2">Citations:</p>
                  <div className="space-y-1">
                    {message.citations.map((citation, idx) => (
                      <div
                        key={idx}
                        className="text-xs text-muted-foreground"
                      >
                        {citation.paper_title} (p{citation.page_number})
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {message.role === "user" && (
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                  <User className="h-4 w-4 text-muted-foreground" />
                </div>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-4 justify-start">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
            </div>
            <div className="bg-muted rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
