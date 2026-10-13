import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Search, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "../lib/api";
import { DailyPostState } from "../lib/types";

export const DraftsPage: React.FC = () => {
  const [posts, setPosts] = useState<DailyPostState[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.listPosts()
      .then((res) => setPosts(res.posts))
      .finally(() => setLoading(false));
  }, []);

  const filtered = posts.filter((p) => {
    const text = `${p.date} ${p.pillar_name} ${p.topic} ${p.draft_content || ""}`.toLowerCase();
    return text.includes(query.toLowerCase());
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">Drafts & Outbox Queue</h1>
          <p className="text-sm text-slate-500 mt-1">Review, refine, audit, and approve generated content</p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search drafts or topics..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-sky-500 transition"
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-24 flex justify-center">
            <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">No drafts found</p>
            <p className="text-xs text-slate-400 mt-1">Generate your first daily post to populate the outbox queue.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((p) => (
              <div key={p.date} className="p-5 hover:bg-slate-50/60 transition flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="font-bold text-slate-900">{p.date}</span>
                    <span className="text-slate-300">•</span>
                    <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium">
                      {p.pillar_name}
                    </span>
                    <span className="text-slate-300">•</span>
                    <span className="text-slate-500">{p.draft_content ? `${p.draft_content.length} chars` : "Empty"}</span>
                  </div>
                  <h3 className="font-semibold text-slate-800 text-sm">{p.topic}</h3>
                  {p.draft_content && (
                    <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                      {p.draft_content.slice(0, 200)}...
                    </p>
                  )}
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                      p.draft_status === "approved"
                        ? "bg-purple-100 text-purple-800"
                        : p.draft_status === "saved"
                        ? "bg-sky-100 text-sky-800"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {p.draft_status === "approved" ? "Approved" : "Draft Saved"}
                  </span>

                  <Link
                    to={`/editor/${p.date}`}
                    className="inline-flex items-center px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-sky-50 hover:text-sky-700 text-slate-700 transition"
                  >
                    Edit & Audit <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
