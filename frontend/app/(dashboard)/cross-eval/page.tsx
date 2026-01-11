"use client";

export default function CrossEvalPage() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-2xl font-bold mb-4">Cross Evaluation</h1>
        <p className="text-muted-foreground">Compare responses from multiple LLMs and see evaluation results.</p>
      </div>
    </div>
  );
}

