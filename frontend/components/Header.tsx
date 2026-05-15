"use client";

import { WorkspaceSelector } from "./WorkspaceSelector";
import { Sidebar } from "@/components/Sidebar";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Bell, Search, Menu } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuGroup,
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/stores/authStore";
import { LogOut, User as UserIcon, Settings as SettingsIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export function Header() {
  const router = useRouter();
  const { user, signOut } = useAuth();

  const handleLogout = async () => {
    try {
      await signOut();
      await fetch('/v1/auth/session', { method: 'DELETE' });
      toast.success('Logged out successfully');
      router.push('/login');
    } catch (err) {
      toast.error('Failed to logout');
    }
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-950/50 px-6 backdrop-blur-md">
      <div className="flex items-center gap-4">
        <Sheet>
          <SheetTrigger className="lg:hidden p-2 text-slate-400 hover:text-white transition-colors">
            <Menu className="h-6 w-6" />
          </SheetTrigger>
          <SheetContent side="left" className="p-0 w-64 bg-slate-950 border-r-slate-800">
            <Sidebar />
          </SheetContent>
        </Sheet>
        <WorkspaceSelector />
      </div>

      <div className="flex items-center gap-4">
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="search"
            placeholder="Search resources..."
            className="h-10 w-64 rounded-md border border-slate-800 bg-slate-900/50 pl-9 pr-4 text-sm text-slate-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <Button variant="ghost" size="icon" className="text-slate-400 hover:bg-slate-900 hover:text-white">
          <Bell className="h-5 w-5" />
        </Button>
        
        <div className="h-8 w-px bg-slate-800" />
        
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-3 hover:bg-slate-900 p-1.5 rounded-xl transition-colors outline-none group">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-white group-hover:text-brand-400 transition-colors">
                {user?.displayName || "Guest User"}
              </p>
              <p className="text-xs text-slate-500">{user?.email || "No account"}</p>
            </div>
            <Avatar className="h-9 w-9 border border-slate-800 group-hover:border-brand-500/50 transition-colors">
              <AvatarImage src={user?.photoURL || "https://github.com/shadcn.png"} alt="User" />
              <AvatarFallback className="bg-brand-600 text-white">
                {user?.displayName?.charAt(0) || "U"}
              </AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 bg-slate-950 border-slate-800 text-slate-300">
            <DropdownMenuGroup>
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-slate-800" />
              <DropdownMenuItem className="flex items-center gap-2 hover:bg-slate-900 cursor-pointer" onClick={() => router.push('/settings?tab=profile')}>
                <UserIcon className="w-4 h-4" />
                Profile Settings
              </DropdownMenuItem>
              <DropdownMenuItem className="flex items-center gap-2 hover:bg-slate-900 cursor-pointer" onClick={() => router.push('/settings?tab=workspace')}>
                <SettingsIcon className="w-4 h-4" />
                System Config
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator className="bg-slate-800" />
            <DropdownMenuItem className="flex items-center gap-2 text-rose-400 hover:bg-rose-500/10 hover:text-rose-400 cursor-pointer" onClick={handleLogout}>
              <LogOut className="w-4 h-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
