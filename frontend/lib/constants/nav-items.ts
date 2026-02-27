import { 
  MessageSquare, 
  FileText, 
  CheckCircle, 
  Network, 
  FlaskConical, 
  FileStack, 
  BarChart,
  Workflow
} from "lucide-react";

export type NavItem = {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  href: string;
  badge?: number;
};

export const navItems: NavItem[] = [
  { icon: MessageSquare, label: "Chat", href: "/chat" },
  { icon: FileText, label: "View PDF", href: "/pdf" },
  { icon: CheckCircle, label: "Claim Verify", href: "/claim-verify" },
  { icon: Network, label: "Blueprint Gen", href: "/blueprint" },
  { icon: FlaskConical, label: "Method Reprod", href: "/method-reprod" },
  { icon: FileStack, label: "Literature Cleanup", href: "/literature" },
  { icon: Workflow, label: "Graph", href: "/graph" },
  { icon: BarChart, label: "Cross Eval", href: "/cross-eval" },
];
