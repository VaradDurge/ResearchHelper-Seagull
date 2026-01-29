"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { MessageInput } from "@/components/chat/MessageInput";
import { MessageList, type Message } from "@/components/chat/MessageList";
import { PDFUploader } from "@/components/pdf/PDFUploader";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { importDoi, lookupDois } from "@/lib/api/doi";
import { Loader2, Link as LinkIcon, Download } from "lucide-react";
import { sendMessage } from "@/lib/api/chat";
import { getConversation } from "@/lib/api/conversations";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [doiDialogOpen, setDoiDialogOpen] = useState(false);
  const [doiEntries, setDoiEntries] = useState<
    Array<{
      value: string;
      status: "idle" | "loading" | "success" | "error";
      url?: string;
      pdfUrl?: string;
      title?: string;
      source?: string;
      error?: string;
      importStatus?: "idle" | "loading" | "success" | "error";
      importError?: string;
    }>
  >([{ value: "", status: "idle", importStatus: "idle" }]);
  const [doiLoading, setDoiLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  // Load conversation from URL param
  useEffect(() => {
    const convId = searchParams.get("conversation");
    if (convId && convId !== conversationId) {
      setConversationId(convId);
      loadConversation(convId);
    } else if (!convId && conversationId) {
      // New chat - clear messages
      setMessages([]);
      setConversationId(null);
    }
  }, [searchParams]);

  const loadConversation = async (id: string) => {
    try {
      const conv = await getConversation(id);
      const loadedMessages: Message[] = conv.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations,
        timestamp: new Date(m.created_at),
      }));
      setMessages(loadedMessages);
    } catch {
      // Conversation not found - start fresh
      setMessages([]);
      setConversationId(null);
    }
  };

  const handleSend = async (message: string) => {
    if (!message.trim()) return;
    
    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: message,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    
    try {
      // Call chat API with conversation ID
      const response = await sendMessage(message, undefined, conversationId || undefined);
      
      // Update conversation ID if new
      if (response.conversation_id && response.conversation_id !== conversationId) {
        setConversationId(response.conversation_id);
        router.replace(`/chat?conversation=${response.conversation_id}`, { scroll: false });
      }
      
      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${error.response?.data?.detail || error.message || "Failed to send message"}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadPDF = () => {
    setUploadDialogOpen(true);
  };

  const handleInputDOI = () => {
    setDoiDialogOpen(true);
  };

  const handleUploadSuccess = () => {
    setUploadDialogOpen(false);
    alert("PDF uploaded successfully. You can now chat with it!");
  };

  const handleDoiSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalizeDoi = (doi: string) =>
      doi
        .trim()
        .replace(/^doi:\s*/i, "")
        .replace(/^https?:\/\/doi\.org\//i, "")
        .trim();

    const trimmedDois = doiEntries
      .map(entry => normalizeDoi(entry.value))
      .filter(Boolean);
    if (trimmedDois.length === 0 || doiLoading) return;

    setDoiLoading(true);
    setDoiEntries(prev =>
      prev.map(entry =>
        entry.value.trim()
          ? { ...entry, status: "loading", error: undefined, url: undefined }
          : entry
      )
    );

    try {
      const response = await lookupDois(trimmedDois);
      setDoiEntries(prev =>
        prev.map(entry => {
          const normalized = normalizeDoi(entry.value);
          const result = response.results.find(item => item.doi === normalized);
          if (!entry.value.trim()) return entry;
          if (!result) {
            return {
              ...entry,
              status: "error",
              error: "No result found",
            };
          }
          if (result.error) {
            return {
              ...entry,
              status: "error",
              error: result.error,
            };
          }
          return {
            ...entry,
            status: "success",
            url: result.url,
            pdfUrl: result.pdf_url,
            title: result.title,
            source: result.source,
            importStatus: "idle",
            importError: undefined,
          };
        })
      );
    } catch (error: any) {
      setDoiEntries(prev =>
        prev.map(entry =>
          entry.value.trim()
            ? {
                ...entry,
                status: "error",
                error:
                  error?.response?.data?.detail ||
                  error?.message ||
                  "DOI lookup failed",
              }
            : entry
        )
      );
    } finally {
      setDoiLoading(false);
    }
  };

  const handleAddDoiField = () => {
    setDoiEntries(prev =>
      prev.length >= 5 ? prev : [...prev, { value: "", status: "idle" }]
    );
  };

  const handleDoiChange = (index: number, value: string) => {
    setDoiEntries(prev =>
      prev.map((item, idx) =>
        idx === index
          ? {
              ...item,
              value,
              status: "idle",
              url: undefined,
              pdfUrl: undefined,
              title: undefined,
              source: undefined,
              error: undefined,
              importStatus: "idle",
              importError: undefined,
            }
          : item
      )
    );
  };

  const handleDoiImport = async (index: number) => {
    const entry = doiEntries[index];
    if (!entry || entry.importStatus === "loading") return;
    const normalizeDoi = (doi: string) =>
      doi
        .trim()
        .replace(/^doi:\s*/i, "")
        .replace(/^https?:\/\/doi\.org\//i, "")
        .trim();
    const normalized = normalizeDoi(entry.value);
    if (!normalized) return;

    setDoiEntries(prev =>
      prev.map((item, idx) =>
        idx === index
          ? { ...item, importStatus: "loading", importError: undefined }
          : item
      )
    );

    try {
      await importDoi(normalized);
      setDoiEntries(prev =>
        prev.map((item, idx) =>
          idx === index
            ? { ...item, importStatus: "success", importError: undefined }
            : item
        )
      );
    } catch (error: any) {
      setDoiEntries(prev =>
        prev.map((item, idx) =>
          idx === index
            ? {
                ...item,
                importStatus: "error",
                importError:
                  error?.response?.data?.detail ||
                  error?.message ||
                  "Import failed",
              }
            : item
        )
      );
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages Area */}
      <MessageList messages={messages} isLoading={loading} />
      
      {/* Input Area - Fixed at bottom */}
      <div className="border-t bg-background/95 backdrop-blur">
        <div className="max-w-3xl mx-auto p-4">
          <MessageInput 
            onSend={handleSend}
            onUploadPDF={handleUploadPDF}
            onInputDOI={handleInputDOI}
            disabled={loading}
            placeholder="Message your papers..."
          />
        </div>
      </div>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Upload PDF</DialogTitle>
          </DialogHeader>
          <PDFUploader
            onUploadSuccess={handleUploadSuccess}
            onUploadError={(error) => {
              alert(`Upload failed: ${error}`);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* DOI Dialog */}
      <Dialog open={doiDialogOpen} onOpenChange={setDoiDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Input DOI</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleDoiSubmit} className="space-y-4">
            <div className="space-y-3">
              {doiEntries.map((entry, index) => (
                <div key={index} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Input
                      value={entry.value}
                      onChange={(e) => handleDoiChange(index, e.target.value)}
                      placeholder="10.0000/abcd.12345"
                      autoFocus={index === 0}
                    />
                    {entry.status === "loading" && (
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    )}
                  </div>
                  {entry.status === "success" && (
                    <div className="text-xs text-muted-foreground space-y-1">
                      {entry.url ? (
                        <div className="flex items-center gap-1">
                          <LinkIcon className="h-3 w-3" />
                          <a
                            href={entry.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary underline"
                          >
                            {entry.title || entry.url}
                          </a>
                          {entry.source && <span>({entry.source})</span>}
                        </div>
                      ) : (
                        <div>Metadata found, but no landing page URL.</div>
                      )}
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => handleDoiImport(index)}
                          disabled={
                            entry.importStatus === "loading" ||
                            entry.importStatus === "success"
                          }
                        >
                          {entry.importStatus === "loading" ? (
                            <>
                              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                              Importing...
                            </>
                          ) : entry.importStatus === "success" ? (
                            "Imported"
                          ) : (
                            <>
                              <Download className="mr-2 h-3 w-3" />
                              One-click import
                            </>
                          )}
                        </Button>
                        {entry.importError && (
                          <span className="text-xs text-destructive">
                            {entry.importError}
                          </span>
                        )}
                        {!entry.pdfUrl && entry.importStatus === "idle" && (
                          <span className="text-xs text-muted-foreground">
                            No open-access PDF found.
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  {entry.status === "error" && (
                    <div className="text-xs text-destructive">
                      {entry.error || "Lookup failed"}
                    </div>
                  )}
                </div>
              ))}
              <div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleAddDoiField}
                  disabled={doiEntries.length >= 5}
                >
                  +
                </Button>
                <span className="ml-2 text-xs text-muted-foreground">
                  {doiEntries.length}/5
                </span>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setDoiDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  doiEntries.every(entry => !entry.value.trim()) || doiLoading
                }
              >
                {doiLoading ? "Searching..." : "Submit"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
