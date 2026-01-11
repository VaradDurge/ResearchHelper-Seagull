"use client";

export default function LiteraturePage() {
  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-2xl font-bold mb-4">Literature Cleanup</h1>
        <p className="text-muted-foreground">Group papers by similarity, deduplicate references, and see trends.</p>
      </div>
    </div>
  );
}

