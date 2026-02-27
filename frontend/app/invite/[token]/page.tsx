"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { acceptInvitation } from "@/lib/api/workspace";
import { getCurrentUser, loginWithGoogle } from "@/lib/api/auth";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

type Status = "checking" | "needs_auth" | "accepting" | "success" | "error";

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const [status, setStatus] = useState<Status>("checking");
  const [errorMsg, setErrorMsg] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const buttonRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (!token) return;
    localStorage.setItem("pending_invite_token", token);

    const authToken = localStorage.getItem("auth_token");
    if (!authToken) {
      setStatus("needs_auth");
      return;
    }

    getCurrentUser()
      .then(() => doAccept(token))
      .catch(() => {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        setStatus("needs_auth");
      });
  }, [token]);

  useEffect(() => {
    if (status !== "needs_auth") return;

    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setErrorMsg("Missing NEXT_PUBLIC_GOOGLE_CLIENT_ID");
      setStatus("error");
      return;
    }

    const scriptId = "google-identity-services";
    if (document.getElementById(scriptId)) {
      renderGoogleButton(clientId);
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => renderGoogleButton(clientId);
    script.onerror = () => {
      setErrorMsg("Failed to load Google login script");
      setStatus("error");
    };
    document.body.appendChild(script);
  }, [status]);

  const renderGoogleButton = (clientId: string) => {
    if (!buttonRef.current || !window.google?.accounts?.id) return;
    if (initializedRef.current) return;
    initializedRef.current = true;
    buttonRef.current.innerHTML = "";

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        try {
          const auth = await loginWithGoogle(response.credential);
          localStorage.setItem("auth_token", auth.access_token);
          localStorage.setItem("auth_user", JSON.stringify(auth.user));

          const pending = localStorage.getItem("pending_invite_token");
          if (pending) {
            await doAccept(pending);
          }
        } catch (err: any) {
          setErrorMsg(err?.response?.data?.detail || err?.message || "Login failed");
          setStatus("error");
        }
      },
    });
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "filled_black",
      size: "large",
      text: "continue_with",
      shape: "pill",
      width: 280,
    });
  };

  const doAccept = async (inviteToken: string) => {
    setStatus("accepting");
    try {
      const result = await acceptInvitation(inviteToken);
      setWorkspaceName(result.workspace.name);
      localStorage.removeItem("pending_invite_token");
      localStorage.setItem("active_workspace_id", result.workspace.id);
      setStatus("success");
      setTimeout(() => router.push("/chat"), 2000);
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail || err?.message || "Failed to accept invitation"
      );
      setStatus("error");
      localStorage.removeItem("pending_invite_token");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background text-foreground">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 shadow-lg text-center">
        {status === "checking" && (
          <>
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">Verifying invitation...</p>
          </>
        )}

        {status === "needs_auth" && (
          <>
            <h1 className="text-xl font-semibold mb-2">Sign in to accept invitation</h1>
            <p className="text-sm text-muted-foreground mb-6">
              Continue with Google to join the shared workspace.
            </p>
            <div className="flex flex-col items-center">
              <div ref={buttonRef} />
            </div>
          </>
        )}

        {status === "accepting" && (
          <>
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
            <p className="mt-4 text-sm text-muted-foreground">Joining workspace...</p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle2 className="mx-auto h-10 w-10 text-green-500" />
            <h2 className="mt-4 text-lg font-semibold">You're in!</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              You've joined <strong>{workspaceName}</strong>. Redirecting...
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle className="mx-auto h-10 w-10 text-destructive" />
            <h2 className="mt-4 text-lg font-semibold">Something went wrong</h2>
            <p className="mt-1 text-sm text-muted-foreground">{errorMsg}</p>
            <Button className="mt-4" onClick={() => router.push("/chat")}>
              Go to Dashboard
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
