import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Calendar,
  FileText,
  PlusCircle,
  Search,
  Compass,
  History,
  Activity,
  Settings,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { ConnectionStatus } from "../lib/types";

interface SidebarProps {
  connections?: ConnectionStatus;
  mode?: string;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ connections, mode = "draft_only", isOpen = true, onClose }) => {
  const navItems = [
    { name: "Overview", path: "/", icon: LayoutDashboard },
    { name: "Content Calendar", path: "/calendar", icon: Calendar },
    { name: "Drafts & Queue", path: "/drafts", icon: FileText },
    { name: "New Post", path: "/new-post", icon: PlusCircle },
    { name: "Research & Sources", path: "/research", icon: Search },
    { name: "Content Strategy", path: "/strategy", icon: Compass },
    { name: "Publishing History", path: "/history", icon: History },
    { name: "Run Logs", path: "/logs", icon: Activity },
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200 flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold shadow-md shadow-sky-600/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-slate-900 text-base leading-tight tracking-tight">FounderOS</h1>
            <p className="text-xs text-slate-500 font-medium">LinkedIn Studio</p>
          </div>
        </div>
      </div>

      {/* Mode Status Pill */}
      <div className="px-5 py-3 bg-slate-50 border-b border-slate-100">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500 font-medium">Publishing Mode:</span>
          {mode === "auto_publish" ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-800">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5 animate-pulse"></span>
              Auto-Publish
            </span>
          ) : (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full font-semibold bg-sky-50 text-sky-700">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-sky-600" />
              Draft Only
            </span>
          )}
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-sky-50 text-sky-700 font-semibold shadow-sm shadow-sky-100"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
              }`
            }
          >
            <item.icon className="w-4 h-4 mr-3 shrink-0 text-slate-500 group-hover:text-slate-700" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Connection Health Pill */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/50">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5">Platform Status</p>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-600">Groq LLM</span>
            <span className={`flex items-center font-medium ${connections?.groq === "configured" ? "text-emerald-600" : "text-amber-600"}`}>
              {connections?.groq === "configured" ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Ready
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 mr-1" /> Not set
                </>
              )}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-600">LinkedIn API</span>
            <span className={`flex items-center font-medium ${connections?.linkedin === "connected" ? "text-emerald-600" : "text-amber-600"}`}>
              {connections?.linkedin === "connected" ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Ready
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 mr-1" /> Not set
                </>
              )}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-600">GitHub State</span>
            <span className={`flex items-center font-medium ${connections?.github === "healthy" ? "text-emerald-600" : "text-amber-600"}`}>
              {connections?.github === "healthy" ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Synced
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 mr-1" /> Not set
                </>
              )}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
