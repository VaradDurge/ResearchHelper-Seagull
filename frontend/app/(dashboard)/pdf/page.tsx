"use client";

import { useEffect, useState } from "react";
import { FileText, Trash2, Eye, Calendar, User } from "lucide-react";
import { getPapers, deletePaper } from "@/lib/api/papers";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Paper } from "@/types/paper";
import { useWorkspace } from "@/store/workspaceStore";
import { useWSEvent } from "@/lib/ws/WebSocketProvider";

const formatDate = (value: string | undefined | null) => {
  if (!value) return "";
  const d = new Date(value);
  return isNaN(d.getTime()) ? value : d.toLocaleDateString();
};

export default function PDFPage() {
  const { activeWorkspace } = useWorkspace();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewingPaper, setViewingPaper] = useState<Paper | null>(null);

  // Real-time: refresh papers when a collaborator adds or deletes one
  useWSEvent("paper_added", () => {
    loadPapers();
  });

  useWSEvent("paper_deleted", (event) => {
    const paperId = event.payload?.paper_id;
    if (paperId) {
      setPapers((prev) => prev.filter((p) => p.id !== paperId));
    }
  });

  const loadPapers = async () => {
    try {
      const data = await getPapers();
      setPapers(data.papers);
    } catch {
      // Not logged in or error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadPapers();
  }, [activeWorkspace?.id]);

  const handleDelete = async (paperId: string) => {
    if (!confirm("Are you sure you want to delete this paper?")) return;
    try {
      await deletePaper(paperId);
      setPapers((prev) => prev.filter((p) => p.id !== paperId));
    } catch {
      alert("Failed to delete paper");
    }
  };

  const handleView = (paper: Paper) => {
    setViewingPaper(paper);
  };

  const getPdfUrl = (paperId: string) => {
    const token = localStorage.getItem("auth_token");
    return `http://localhost:8000/api/v1/files/papers/${paperId}?token=${token}`;
  };

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-8rem)] items-center justify-center">
        <p className="text-muted-foreground">Loading papers...</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">View PDF</h1>
            <p className="text-muted-foreground">
              View and manage your uploaded papers.
            </p>
          </div>
          <Button variant="outline" onClick={loadPapers}>
            Refresh
          </Button>
        </div>

        {papers.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">No papers uploaded</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Upload papers from the Chat page to view them here.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {papers.map((paper) => (
              <Card key={paper.id} className="flex flex-col">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base line-clamp-2">
                    {paper.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 space-y-2 text-sm text-muted-foreground">
                  {paper.authors && paper.authors.length > 0 && (
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span className="line-clamp-1">
                        {paper.authors.join(", ")}
                      </span>
                    </div>
                  )}
                  {(paper.publication_date ||
                    (paper.metadata &&
                      typeof paper.metadata.publication_date === "string")) && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      <span>
                        <span className="font-medium text-foreground">
                          Publish Date:
                        </span>{" "}
                        {formatDate(
                          (paper.metadata &&
                            (paper.metadata.publication_date as string)) ||
                            paper.publication_date
                        )}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    <span>
                      <span className="font-medium text-foreground">
                        Upload Date:
                      </span>{" "}
                      {formatDate(paper.upload_date)}
                    </span>
                  </div>
                  {paper.metadata?.num_pages && (
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span>{paper.metadata.num_pages} pages</span>
                    </div>
                  )}
                </CardContent>
                <CardFooter className="pt-2 gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleView(paper)}
                  >
                    <Eye className="h-4 w-4 mr-1" />
                    View
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(paper.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* PDF Viewer Dialog */}
      <Dialog open={!!viewingPaper} onOpenChange={() => setViewingPaper(null)}>
        <DialogContent className="max-w-5xl h-[90vh]">
          <DialogHeader>
            <DialogTitle className="line-clamp-1">
              {viewingPaper?.title}
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 h-full min-h-0">
            {viewingPaper && (
              <iframe
                src={getPdfUrl(viewingPaper.id)}
                className="w-full h-[calc(90vh-100px)] border rounded"
                title={viewingPaper.title}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

