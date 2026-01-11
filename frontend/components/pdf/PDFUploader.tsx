/**
 * # PDFUploader Component
 * 
 * Handles PDF file uploads with drag-and-drop support.
 */
"use client";

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Upload, X, FileText } from "lucide-react";

interface PDFUploaderProps {
  onUploadSuccess?: () => void;
  onUploadError?: (error: string) => void;
}

export function PDFUploader({ onUploadSuccess, onUploadError }: PDFUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files) return;
    
    const pdfFiles = Array.from(files).filter(file => 
      file.type === "application/pdf" || file.name.endsWith(".pdf")
    );
    
    if (pdfFiles.length !== files.length) {
      alert("Only PDF files are allowed");
    }
    
    setSelectedFiles(prev => [...prev, ...pdfFiles]);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
  }, [handleFileSelect]);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;
    
    setUploading(true);
    
    try {
      // Dynamically import to avoid issues if API not ready
      const { uploadPaper } = await import("@/lib/api/papers");
      
      for (const file of selectedFiles) {
        await uploadPaper(file);
      }
      
      setSelectedFiles([]);
      onUploadSuccess?.();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || "Upload failed";
      onUploadError?.(errorMessage);
    } finally {
      setUploading(false);
    }
  }, [selectedFiles, onUploadSuccess, onUploadError]);

  return (
    <div className="space-y-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25"}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          onChange={handleFileInputChange}
          className="hidden"
        />
        
        <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
        <p className="text-sm text-muted-foreground mb-2">
          Drag and drop PDF files here, or click to select
        </p>
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          Select PDFs
        </Button>
      </div>

      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Selected files:</p>
          {selectedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-muted rounded-lg"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </span>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeFile(index)}
                disabled={uploading}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          
          <Button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full"
          >
            {uploading ? "Uploading..." : `Upload ${selectedFiles.length} file(s)`}
          </Button>
        </div>
      )}
    </div>
  );
}
