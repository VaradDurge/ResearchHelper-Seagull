"use client";

import { useState, useEffect, useRef } from "react";
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
import { useWorkspace } from "@/store/workspaceStore";
import { useWSEvent } from "@/lib/ws/WebSocketProvider";
import { useTypingIndicator } from "@/lib/ws/useTypingIndicator";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { activeWorkspace } = useWorkspace();
  const prevWorkspaceRef = useRef(activeWorkspace?.id);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [doiDialogOpen, setDoiDialogOpen] = useState(false);
  const [doiEntry, setDoiEntry] = useState<{
    value: string;
    status: "idle" | "loading" | "success" | "error";
    url?: string;
    pdfUrl?: string;
    title?: string;
    authors?: string[];
    source?: string;
    error?: string;
    importStatus?: "idle" | "loading" | "success" | "error";
    importError?: string;
  }>({ value: "", status: "idle", importStatus: "idle" });
  const [doiLoading, setDoiLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const { typingUsers, onTyping } = useTypingIndicator();

  // Listen for real-time messages from collaborators
  useWSEvent("new_message", (event) => {
    const p = event.payload;
    if (!p) return;
    const userMsg: Message = {
      id: `ws-user-${Date.now()}`,
      role: "user",
      content: p.message,
      timestamp: new Date(),
    };
    const assistantMsg: Message = {
      id: `ws-asst-${Date.now()}`,
      role: "assistant",
      content: p.answer,
      citations: p.citations,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    if (p.conversation_id && !conversationId) {
      setConversationId(p.conversation_id);
    }
  });

  // Clear chat when workspace changes
  useEffect(() => {
    const wsId = activeWorkspace?.id;
    if (prevWorkspaceRef.current && wsId && wsId !== prevWorkspaceRef.current) {
      setMessages([]);
      setConversationId(null);
      router.replace("/chat", { scroll: false });
    }
    prevWorkspaceRef.current = wsId;
  }, [activeWorkspace?.id, router]);

  // Load conversation from URL param
  useEffect(() => {
    const convId = searchParams.get("conversation");
    if (convId && convId !== conversationId) {
      setConversationId(convId);
      loadConversation(convId);
    } else if (!convId && conversationId) {
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

    const normalized = normalizeDoi(doiEntry.value);
    if (!normalized || doiLoading) return;

    setDoiLoading(true);
    setDoiEntry(prev => ({
      ...prev,
      status: "loading",
      error: undefined,
      url: undefined,
      pdfUrl: undefined,
      title: undefined,
      authors: undefined,
      source: undefined,
      importStatus: "idle",
      importError: undefined,
    }));

    try {
      const response = await lookupDois([normalized]);
      const result = response.results.find(item => item.doi === normalized);
      if (!result) {
        setDoiEntry(prev => ({
          ...prev,
          status: "error",
          error: "No result found",
        }));
      } else if (result.error) {
        setDoiEntry(prev => ({
          ...prev,
          status: "error",
          error: result.error,
        }));
      } else {
        setDoiEntry(prev => ({
          ...prev,
          status: "success",
          url: result.url,
          pdfUrl: result.pdf_url,
          title: result.title,
          authors: result.authors,
          source: result.source,
          importStatus: "idle",
          importError: undefined,
        }));
      }
    } catch (error: any) {
      setDoiEntry(prev => ({
        ...prev,
        status: "error",
        error:
          error?.response?.data?.detail ||
          error?.message ||
          "DOI lookup failed",
      }));
    } finally {
      setDoiLoading(false);
    }
  };

  const handleDoiChange = (value: string) => {
    setDoiEntry(prev => ({
      ...prev,
      value,
      status: "idle",
      url: undefined,
      pdfUrl: undefined,
      title: undefined,
      authors: undefined,
      source: undefined,
      error: undefined,
      importStatus: "idle",
      importError: undefined,
    }));
  };

  const handleDoiImport = async () => {
    if (doiEntry.importStatus === "loading") return;
    const normalizeDoi = (doi: string) =>
      doi
        .trim()
        .replace(/^doi:\s*/i, "")
        .replace(/^https?:\/\/doi\.org\//i, "")
        .trim();
    const normalized = normalizeDoi(doiEntry.value);
    if (!normalized) return;

    setDoiEntry(prev => ({
      ...prev,
      importStatus: "loading",
      importError: undefined,
    }));

    try {
      await importDoi(normalized);
      setDoiEntry(prev => ({
        ...prev,
        importStatus: "success",
        importError: undefined,
      }));
    } catch (error: any) {
      setDoiEntry(prev => ({
        ...prev,
        importStatus: "error",
        importError:
          error?.response?.data?.detail ||
          error?.message ||
          "Import failed",
      }));
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages Area */}
      <MessageList messages={messages} isLoading={loading} />
      
      {/* Floating query dock */}
      <div className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex justify-center px-4">
        <div className="pointer-events-auto w-full max-w-2xl">
          {typingUsers.length > 0 && (
            <p className="mb-2 text-xs text-muted-foreground animate-pulse text-center">
              A collaborator is typing...
            </p>
          )}
          <MessageInput 
            onSend={handleSend}
            onUploadPDF={handleUploadPDF}
            onInputDOI={handleInputDOI}
            onTyping={onTyping}
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
            <DialogTitle>DOI Import</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleDoiSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                value={doiEntry.value}
                onChange={(e) => handleDoiChange(e.target.value)}
                placeholder="https://doi.org/10.0000/abcd.12345"
                autoFocus
              />
              {doiEntry.status === "success" && (
                <div className="text-xs text-muted-foreground space-y-1">
                  {doiEntry.title && (
                    <div className="font-medium text-foreground">{doiEntry.title}</div>
                  )}
                  {doiEntry.authors && doiEntry.authors.length > 0 && (
                    <div>{doiEntry.authors.slice(0, 3).join(", ")}</div>
                  )}
                  {doiEntry.url ? (
                    <div className="flex items-center gap-1">
                      <LinkIcon className="h-3 w-3" />
                      <a
                        href={doiEntry.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary underline"
                      >
                        {doiEntry.url}
                      </a>
                      {doiEntry.source && <span>({doiEntry.source})</span>}
                    </div>
                  ) : (
                    <div>Metadata found, but no landing page URL.</div>
                  )}
                </div>
              )}
              {doiEntry.status === "error" && (
                <div className="text-xs text-destructive">
                  {doiEntry.error || "Lookup failed"}
                </div>
              )}
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
                  !doiEntry.value.trim() || doiLoading
                }
              >
                {doiLoading && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin text-green-500" />
                )}
                {doiLoading ? "Searching..." : "Submit"}
              </Button>
            </div>
            {doiEntry.status === "success" && (
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleDoiImport}
                  disabled={
                    doiEntry.importStatus === "loading" ||
                    doiEntry.importStatus === "success"
                  }
                >
                  {doiEntry.importStatus === "loading" ? (
                    <>
                      <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                      Importing...
                    </>
                  ) : doiEntry.importStatus === "success" ? (
                    "Imported"
                  ) : (
                    <>
                      <Download className="mr-2 h-3 w-3" />
                      Import
                    </>
                  )}
                </Button>
                {doiEntry.importError && (
                  <span className="text-xs text-destructive">
                    {doiEntry.importError}
                  </span>
                )}
                {!doiEntry.pdfUrl && doiEntry.importStatus === "idle" && (
                  <span className="text-xs text-muted-foreground">
                    No open-access PDF found.
                  </span>
                )}
              </div>
            )}
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
