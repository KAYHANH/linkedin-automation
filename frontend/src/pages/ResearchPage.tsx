import React, { useEffect, useState } from "react";
import { Search, ExternalLink, ShieldCheck, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "../lib/api";
import { DailyPostState } from "../lib/types";

export const ResearchPage: React.FC = () => {
  const [posts, setPosts] = useState<DailyPostState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listPosts()
      .then((res) => setPosts(res.posts))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">Research & Verified Sources</h1>
        <p className="text-sm text-slate-500 mt-1">
          Tracking sources, verified facts, and evergreen background data utilized in daily posts
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <h2 className="font-bold text-slate-900 text-base mb-4 flex items-center">
          <ShieldCheck className="w-4 h-4 mr-2 text-sky-600" /> Source Citation Guardrails
        </h2>
        <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
          External sources are collected strictly via Groq's browser search or configured verified repositories. Untrusted external data is summarized without reproducing copyright text and cannot trigger publishing actions. When live search is unavailable, the engine falls back to curated evergreen industry contexts.
        </p>
      </div>

      {loading ? (
        <div className="py-24 flex justify-center">
          <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : posts.length === 0 ? (
        <div className="py-20 text-center bg-white rounded-2xl border border-slate-200">
          <Search className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-sm font-semibold text-slate-700">No research records yet</p>
          <p className="text-xs text-slate-400 mt-1">Generated posts will record their source citations here.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((p) => {
            const meta = p.research_metadata;
            return (
              <div key={p.date} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-3 gap-2">
                  <div>
                    <span className="text-xs font-bold text-slate-900">{p.date}</span>
                    <span className="text-slate-400 mx-2">•</span>
                    <span className="text-xs font-semibold text-sky-700">{p.pillar_name}</span>
                    <h3 className="font-semibold text-slate-800 text-sm mt-0.5">{p.topic}</h3>
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded-full text-[10px] font-semibold self-start sm:self-auto ${
                      meta?.is_live_search ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {meta?.is_live_search ? "Live Web Search" : "Evergreen Verified Context"}
                  </span>
                </div>

                {meta?.summary && (
                  <div className="text-xs text-slate-700 bg-slate-50 p-3.5 rounded-xl border border-slate-100 leading-relaxed">
                    <strong>Research Summary:</strong> {meta.summary}
                  </div>
                )}

                {meta?.sources && meta.sources.length > 0 ? (
                  <div className="space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Sources Attached:</span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {meta.sources.map((src, i) => (
                        <div key={i} className="p-3 rounded-xl border border-slate-200 text-xs space-y-1">
                          <p className="font-semibold text-slate-900 flex items-center justify-between">
                            <span>{src.title}</span>
                            {src.url && (
                              <a href={src.url} target="_blank" rel="noreferrer" className="text-sky-600 hover:text-sky-700">
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </p>
                          <p className="text-slate-500 text-[11px]">Publisher: {src.publisher || "Official Source"}</p>
                          <p className="text-slate-600 text-[11px]">Claim: {src.claim}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">No external URLs cited for this post.</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
