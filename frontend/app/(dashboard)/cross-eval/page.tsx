"use client";

import { useState } from "react";
import { MessageInput } from "@/components/chat/MessageInput";
import { MessageList, type Message } from "@/components/chat/MessageList";
import { PDFUploader } from "@/components/pdf/PDFUploader";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { sendCrossEval } from "@/lib/api/cross-eval";

export default function CrossEvalPage() {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

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

