"use client";

import * as React from "react";
import { Check, ChevronsUpDown, PlusCircle, Building2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function WorkspaceSelector() {
  const router = useRouter();
  const { workspaces, selectedWorkspace, setSelectedWorkspace, hydrateWorkspaceState } = useStore();

  React.useEffect(() => {
    hydrateWorkspaceState();
  }, [hydrateWorkspaceState]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex h-10 w-[240px] items-center justify-between rounded-md border border-slate-700 bg-slate-800/50 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800 hover:text-white focus:outline-none focus:ring-1 focus:ring-brand-500"
        )}
      >
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-brand-400" />
          <span className="truncate">{selectedWorkspace}</span>
        </div>
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-[240px] bg-slate-900 border-slate-700 text-slate-200">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-slate-700" />
          {workspaces.map((workspace) => (
            <DropdownMenuItem
              key={workspace.id}
              onClick={() => setSelectedWorkspace(workspace.name)}
              className="flex items-center justify-between hover:bg-slate-800 focus:bg-slate-800 cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                <span>{workspace.name}</span>
              </div>
              {selectedWorkspace === workspace.name && (
                <Check className="h-4 w-4 text-brand-400" />
              )}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
        <DropdownMenuSeparator className="bg-slate-700" />
        <DropdownMenuItem
          onClick={() => router.push('/settings?tab=workspace&mode=create')}
          className="flex items-center gap-2 hover:bg-slate-800 focus:bg-slate-800 cursor-pointer text-brand-400"
        >
          <PlusCircle className="h-4 w-4" />
          <span>Create Workspace</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
