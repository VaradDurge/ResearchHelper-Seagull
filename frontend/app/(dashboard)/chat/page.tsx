"use client";

import { useState } from "react";
import { MessageInput } from "@/components/chat/MessageInput";
import { MessageList, type Message } from "@/components/chat/MessageList";
import { PDFUploader } from "@/components/pdf/PDFUploader";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { sendMessage } from "@/lib/api/chat";

export default function ChatPage() {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

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
      // Call chat API
      const response = await sendMessage(message);
      
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
    // TODO: Implement DOI input dialog
    alert("DOI import will be available soon");
  };

  const handleUploadSuccess = () => {
    setUploadDialogOpen(false);
    alert("PDF uploaded successfully. You can now chat with it!");
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
    </div>
  );
}
