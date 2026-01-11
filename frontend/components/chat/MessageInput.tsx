"use client";

import { useState, useRef, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Send, Plus, Upload, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface MessageInputProps {
  onSend?: (message: string) => void;
  onUploadPDF?: () => void;
  onInputDOI?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({
  onSend,
  onUploadPDF,
  onInputDOI,
  disabled = false,
  placeholder = "Input Query",
}: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [popoverOpen, setPopoverOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend?.(message.trim());
      setMessage("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-center gap-2 rounded-full border-0 bg-background/95 backdrop-blur-sm p-1.5 shadow-2xl">
        <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 shrink-0 rounded-full hover:bg-accent transition-all"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent 
            className="w-48 p-2" 
            align="start"
            side="top"
            sideOffset={8}
          >
            <div className="flex flex-col gap-1">
              <Button
                type="button"
                variant="ghost"
                className="w-full justify-start gap-2"
                onClick={() => {
                  onUploadPDF?.();
                  setPopoverOpen(false);
                }}
              >
                <Upload className="h-4 w-4" />
                Upload PDFs
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full justify-start gap-2"
                onClick={() => {
                  onInputDOI?.();
                  setPopoverOpen(false);
                }}
              >
                <FileText className="h-4 w-4" />
                Input DOI
              </Button>
            </div>
          </PopoverContent>
        </Popover>
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            "min-h-[44px] max-h-[200px] resize-none border-0 bg-transparent px-4 py-2.5 text-sm",
            "focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-0",
            "placeholder:text-muted-foreground",
            "shadow-none outline-none"
          )}
          rows={1}
        />
        <Button
          type="submit"
          disabled={disabled || !message.trim()}
          size="icon"
          className="h-9 w-9 shrink-0 rounded-full"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </form>
  );
}
