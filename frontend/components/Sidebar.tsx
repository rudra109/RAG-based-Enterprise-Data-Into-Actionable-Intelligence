"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  MessageSquare, 
  GitBranch, 
  BarChart3, 
  AlertTriangle, 
  TrendingUp, 
  Network, 
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

const navItems = [
  { name: "RAG Chat", href: "/chat", icon: MessageSquare },
  { name: "Pipelines", href: "/pipelines", icon: GitBranch },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Anomalies", href: "/anomalies", icon: AlertTriangle },
  { name: "Forecasting", href: "/forecasting", icon: TrendingUp },
  { name: "Knowledge Graph", href: "/graph", icon: Network },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isSidebarOpen, toggleSidebar } = useStore();

  return (
    <div
      className={cn(
        "relative flex flex-col border-r border-slate-800 bg-slate-950 text-slate-400 transition-all duration-300",
        isSidebarOpen ? "w-64" : "w-20"
      )}
    >
      <div className="flex h-16 items-center px-6">
        <Link href="/" className="flex items-center gap-2 font-bold text-white">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
            <Zap className="h-5 w-5 text-white" />
          </div>
          {isSidebarOpen && <span className="text-xl tracking-tight">EnterpriseIQ</span>}
        </Link>
      </div>

      <ScrollArea className="flex-1 px-3">
        <div className="space-y-2 py-4">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-slate-900 hover:text-white",
                  isActive ? "bg-brand-600/10 text-brand-400" : "text-slate-400",
                  !isSidebarOpen && "justify-center"
                )}
              >
                <item.icon className={cn("h-5 w-5", isActive ? "text-brand-400" : "text-slate-400")} />
                {isSidebarOpen && <span>{item.name}</span>}
                {isActive && isSidebarOpen && (
                  <div className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-400" />
                )}
              </Link>
            );
          })}
        </div>
      </ScrollArea>

      <div className="border-t border-slate-800 p-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-9 w-9 text-slate-400 hover:bg-slate-900 hover:text-white"
        >
          {isSidebarOpen ? (
            <ChevronLeft className="h-5 w-5" />
          ) : (
            <ChevronRight className="h-5 w-5" />
          )}
        </Button>
      </div>
    </div>
  );
}
