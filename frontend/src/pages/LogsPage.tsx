import React, { useEffect, useState } from "react";
import { Activity, AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { RunLog } from "../lib/types";

export const LogsPage: React.FC = () => {
  const [runs, setRuns] = useState<RunLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRuns()
      .then((res) => setRuns(res.runs))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">System Run Logs</h1>
        <p className="text-sm text-slate-500 mt-1">
          Safe operational records from cron and manual runs stored in GitHub automation history
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs flex items-center justify-between text-xs text-slate-600">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>All operational logs automatically redact authorization tokens, client secrets, and passwords.</span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-24 flex justify-center">
            <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : runs.length === 0 ? (
          <div className="py-20 text-center">
            <Activity className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">No execution logs found</p>
            <p className="text-xs text-slate-400 mt-1">Runs are archived to the GitHub state branch automatically.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-6 py-3.5">Execution Date</th>
                  <th className="px-6 py-3.5">Content Topic</th>
                  <th className="px-6 py-3.5">Draft Status</th>
                  <th className="px-6 py-3.5">Publish Status</th>
                  <th className="px-6 py-3.5">Execution Mode</th>
                  <th className="px-6 py-3.5">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50/60 transition">
                    <td className="px-6 py-4 font-bold text-slate-900">{r.date}</td>
                    <td className="px-6 py-4 max-w-xs truncate">{r.topic || "Daily Rotation"}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-0.5 rounded font-semibold bg-sky-50 text-sky-700">
                        {r.draft_status || "saved"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-0.5 rounded font-semibold ${
                          r.publication_status === "published"
                            ? "bg-emerald-50 text-emerald-700"
                            : r.publication_status === "failed"
                            ? "bg-rose-50 text-rose-700"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {r.publication_status || "not_started"}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-[11px] text-slate-500">{r.execution_mode || "cron"}</td>
                    <td className="px-6 py-4 text-slate-400">{r.updated_at ? r.updated_at.split("T")[0] : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
