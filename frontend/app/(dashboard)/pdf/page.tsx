"use client";

export default function PDFPage() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-2xl font-bold mb-4">View PDF</h1>
        <p className="text-muted-foreground">View and manage your uploaded papers.</p>
      </div>
    </div>
  );
}

