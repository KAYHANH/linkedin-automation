import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Lock, User, AlertCircle, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState("founder");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await api.login(username, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Invalid credentials. Please verify username and password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-800/90 border border-slate-700/80 rounded-2xl p-8 shadow-2xl backdrop-blur-xl">
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-xl bg-sky-500 items-center justify-center text-white mb-3 shadow-lg shadow-sky-500/30">
            <Sparkles className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">FounderOS LinkedIn Studio</h1>
          <p className="text-sm text-slate-400 mt-1">Single-founder content command center</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Founder Username
            </label>
            <div className="relative">
              <User className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700 text-white rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition"
                placeholder="founder"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="w-5 h-5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700 text-white rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-sky-500 hover:bg-sky-400 text-slate-950 font-semibold rounded-xl py-3 text-sm transition-all shadow-lg shadow-sky-500/20 disabled:opacity-50 flex items-center justify-center space-x-2"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-slate-900 border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Enter Studio</span>
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-700/60 text-center">
          <p className="text-xs text-slate-400">
            Protected internal admin dashboard. Password hash is checked on server-side.
          </p>
        </div>
      </div>
    </div>
  );
};
