"use client";

import { useState } from "react";
import { MessageInput } from "@/components/chat/MessageInput";
import { MessageList, type Message } from "@/components/chat/MessageList";
import { PDFUploader } from "@/components/pdf/PDFUploader";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { sendCrossEval } from "@/lib/api/cross-eval";
import { useWSEvent } from "@/lib/ws/WebSocketProvider";

export default function CrossEvalPage() {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  useWSEvent("cross_eval_result", (event) => {
    const p = event.payload;
    if (!p) return;
    const userMsg: Message = {
      id: `ws-ce-user-${Date.now()}`,
      role: "user",
      content: p.question,
      timestamp: new Date(),
    };
    const assistantMsg: Message = {
      id: `ws-ce-asst-${Date.now()}`,
      role: "assistant",
      content: p.answer,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
  });

  const handleSend = async (message: string) => {
    if (!message.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: message,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await sendCrossEval(message);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
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
    alert("DOI import will be available soon");
  };

  const handleUploadSuccess = () => {
    setUploadDialogOpen(false);
    alert("PDF uploaded successfully. You can now chat with it!");
  };

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} isLoading={loading} />

      <div className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex justify-center px-4">
        <div className="pointer-events-auto w-full max-w-2xl">
          <MessageInput
            onSend={handleSend}
            onUploadPDF={handleUploadPDF}
            onInputDOI={handleInputDOI}
            disabled={loading}
            placeholder="Message your papers..."
          />
        </div>
      </div>

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
    </div>
  );
}

