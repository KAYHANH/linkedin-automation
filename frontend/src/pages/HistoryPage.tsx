import React, { useEffect, useState } from "react";
import { History, ExternalLink, CheckCircle2 } from "lucide-react";
import { api } from "../lib/api";
import { DailyPostState } from "../lib/types";

export const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<DailyPostState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getHistory()
      .then((res) => setHistory(res.history))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">Confirmed Publishing History</h1>
        <p className="text-sm text-slate-500 mt-1">
          Historical record of posts confirmed published to LinkedIn via official API responses
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-24 flex justify-center">
            <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : history.length === 0 ? (
          <div className="py-20 text-center">
            <History className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">No published posts recorded yet</p>
            <p className="text-xs text-slate-400 mt-1">
              Posts published via the official LinkedIn API will appear here with confirmed Post URNs.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {history.map((item) => (
              <div key={item.date} className="p-6 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="font-bold text-slate-900">{item.date}</span>
                    <span className="text-slate-300">•</span>
                    <span className="font-semibold text-sky-700">{item.pillar_name}</span>
                    <span className="text-slate-300">•</span>
                    <span className="font-mono text-slate-500 text-[11px]">
                      LinkedIn ID: {item.linkedin_post_id || "Recorded"}
                    </span>
                  </div>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                    <CheckCircle2 className="w-3 h-3 mr-1" /> Published
                  </span>
                </div>

                <h3 className="font-semibold text-slate-800 text-sm">{item.topic}</h3>

                {item.draft_content && (
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-700 whitespace-pre-line leading-relaxed max-h-48 overflow-y-auto">
                    {item.draft_content}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
