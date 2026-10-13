import React, { useState, useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { Navbar } from "../components/Navbar";
import { api } from "../lib/api";
import { DashboardSummary } from "../lib/types";

export const DashboardLayout: React.FC = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [username, setUsername] = useState("founder");

  useEffect(() => {
    // Check session
    api.getSession().then((session) => {
      if (!session.authenticated) {
        navigate("/login");
      } else if (session.username) {
        setUsername(session.username);
      }
    }).catch(() => {
      navigate("/login");
    });

    // Load summary
    api.getDashboardSummary().then((data) => {
      setSummary(data);
    }).catch(() => {
      // Handled silently
    });
  }, [navigate]);

  const handleLogout = async () => {
    await api.logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-xs md:hidden"
        />
      )}

      {/* Left Sidebar */}
      <Sidebar
        connections={summary?.connections}
        mode={summary?.current_mode}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-64 min-w-0">
        <Navbar
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          username={username}
          nextRun={summary?.next_daily_run}
          onLogout={handleLogout}
        />
        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
