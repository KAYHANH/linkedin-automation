import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  CheckCircle,
  Calendar,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Clock,
  Layers,
  Activity,
  Send
} from "lucide-react";
import { api } from "../lib/api";
import { DashboardSummary } from "../lib/types";

export const OverviewPage: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    api.getDashboardSummary()
      .then(setData)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleGenerateToday = async () => {
    setGenerating(true);
    setActionMsg(null);
    try {
      await api.generatePost({ date: data?.today_date });
      setActionMsg("Today's draft successfully generated and audited!");
      loadData();
    } catch (err: any) {
      setActionMsg(`Generation failed: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">LinkedIn Command Center</h1>
          <p className="text-sm text-slate-500 mt-1">
            Automated rotating strategy across 8 founder pillars • Today: <span className="font-semibold text-slate-700">{data?.today_date}</span>
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleGenerateToday}
            disabled={generating}
            className="inline-flex items-center px-4 py-2.5 rounded-xl text-sm font-semibold text-white bg-sky-600 hover:bg-sky-500 shadow-sm shadow-sky-600/20 transition-all disabled:opacity-50"
          >
            {generating ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
            ) : (
              <Sparkles className="w-4 h-4 mr-2" />
            )}
            Generate Today's Draft
          </button>
          <Link
            to="/new-post"
            className="inline-flex items-center px-4 py-2.5 rounded-xl text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-all"
          >
            Custom Post
          </Link>
        </div>
      </div>

      {actionMsg && (
        <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-sky-800 text-sm font-medium flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-sky-600 hover:text-sky-900">&times;</button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Drafts in Queue</span>
            <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">{data?.drafts_waiting_count || 0}</p>
          <p className="text-xs text-slate-500 mt-1">Pending approval or publication</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Published Posts</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2">{data?.posts_published_count || 0}</p>
          <p className="text-xs text-slate-500 mt-1">Live on LinkedIn profile</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Publishing Mode</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-2 capitalize">
            {data?.current_mode === "auto_publish" ? "Auto-Publish" : "Draft Only"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {data?.dry_run ? "Safe dry-run enforced" : "Live publishing allowed"}
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Next Cron Trigger</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="text-lg font-bold text-slate-900 mt-2 truncate">09:00 AM IST</p>
          <p className="text-xs text-slate-500 mt-1 truncate">Schedule: 30 3 * * * UTC</p>
        </div>
      </div>

      {/* Today's Focus Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-sky-500 animate-ping"></div>
            <h2 className="font-bold text-slate-900 text-base">Today's Content Assignment</h2>
          </div>
          {data?.today_state?.draft_content ? (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800">
              Draft Prepared ({data.today_state.draft_content.length} chars)
            </span>
          ) : (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
              Not Generated Yet
            </span>
          )}
        </div>

        {data?.today_state?.draft_content ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-md bg-slate-100 font-medium text-slate-700">
                Pillar: {data.today_state.pillar_name}
              </span>
              <span className="px-2.5 py-1 rounded-md bg-sky-50 font-medium text-sky-700">
                Hook: {data.today_state.hook_formula}
              </span>
              <span className="px-2.5 py-1 rounded-md bg-purple-50 font-medium text-purple-700">
                Angle: {data.today_state.founder_angle}
              </span>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 font-mono text-xs text-slate-700 whitespace-pre-line leading-relaxed max-h-48 overflow-y-auto">
              {data.today_state.draft_content}
            </div>
            <div className="flex justify-end space-x-3 pt-2">
              <Link
                to={`/editor/${data.today_date}`}
                className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold bg-sky-600 text-white hover:bg-sky-500 transition"
              >
                Open in Full Editor &rarr;
              </Link>
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-sm text-slate-600">No draft recorded yet for today's topic.</p>
            <p className="text-xs text-slate-400 mt-1">
              Click <strong>"Generate Today's Draft"</strong> above to produce a post draft via Groq.
            </p>
          </div>
        )}
      </div>

      {/* Two Column Grid: Next 7 Topics + Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Next 7 Topics */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-900 text-base flex items-center">
              <Calendar className="w-4 h-4 mr-2 text-sky-600" /> Next 7 Planned Topics
            </h2>
            <Link to="/calendar" className="text-xs font-semibold text-sky-600 hover:text-sky-700">
              View 30-Day Plan &rarr;
            </Link>
          </div>
          <div className="space-y-3">
            {data?.next_7_topics.map((item, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl border border-slate-100 hover:border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition flex items-start justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900">{item.date}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-semibold">
                      Day {item.day}
                    </span>
                    <span className="text-slate-400">•</span>
                    <span className="text-sky-700 font-medium">{item.pillar_name}</span>
                  </div>
                  <p className="text-slate-600 line-clamp-1">{item.topic}</p>
                </div>
                <Link
                  to={`/editor/${item.date}`}
                  className="text-slate-400 hover:text-sky-600 p-1 shrink-0"
                >
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Items */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-slate-900 text-base flex items-center">
              <Activity className="w-4 h-4 mr-2 text-emerald-600" /> Recent Content Activity
            </h2>
            <Link to="/drafts" className="text-xs font-semibold text-sky-600 hover:text-sky-700">
              View All Drafts &rarr;
            </Link>
          </div>

          {data?.recent_items && data.recent_items.length > 0 ? (
            <div className="space-y-3">
              {data.recent_items.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-0.5 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-900">{item.date}</span>
                      <span className="text-slate-400">•</span>
                      <span className="text-slate-600 truncate">{item.pillar_name}</span>
                    </div>
                    <p className="text-slate-500 truncate">{item.topic}</p>
                  </div>
                  <div className="flex items-center space-x-2 shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        item.publication_status === "published"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-sky-100 text-sky-800"
                      }`}
                    >
                      {item.publication_status === "published" ? "Published" : "Draft"}
                    </span>
                    <Link
                      to={`/editor/${item.date}`}
                      className="p-1 rounded text-slate-400 hover:text-sky-600"
                    >
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs">
              No previous posts or drafts saved yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
