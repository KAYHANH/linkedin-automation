import React from "react";
import { Menu, LogOut, Clock, Globe } from "lucide-react";

interface NavbarProps {
  onToggleSidebar: () => void;
  username?: string;
  nextRun?: string;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar, username = "founder", nextRun, onLogout }) => {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 md:px-8 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 -ml-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 md:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="hidden sm:flex items-center text-xs text-slate-500 space-x-2 bg-slate-100/80 px-3 py-1.5 rounded-full border border-slate-200/50">
          <Globe className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-medium text-slate-700">Asia/Kolkata</span>
          <span className="text-slate-300">•</span>
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Next Cron: <strong className="text-slate-800 font-semibold">{nextRun ? nextRun.split(" ")[1] : "09:00 AM IST"}</strong></span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 font-bold text-xs ring-2 ring-white shadow-sm">
            {username.slice(0, 1).toUpperCase()}
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-xs font-semibold text-slate-900 leading-none">{username}</p>
            <p className="text-[10px] text-slate-500 font-medium">Technology Founder</p>
          </div>
        </div>

        <button
          onClick={onLogout}
          title="Sign out"
          className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
