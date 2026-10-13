import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight, ShieldCheck, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "../lib/api";
import { AuditResult, DailyPostState, PillarInfo } from "../lib/types";

export const NewPostPage: React.FC = () => {
  const navigate = useNavigate();
  const [pillars, setPillars] = useState<PillarInfo[]>([]);
  const [selectedPillar, setSelectedPillar] = useState<string>("");
  const [topic, setTopic] = useState("");
  const [goal, setGoal] = useState("comments");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ state: DailyPostState; audit: AuditResult } | null>(null);

  useEffect(() => {
    api.getStrategy().then((data) => {
      setPillars(data.pillars);
      if (data.pillars.length > 0) {
        setSelectedPillar(data.pillars[0].id);
      }
    });
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.generatePost({
        date,
        topic_override: topic.trim() || undefined,
        pillar_id_override: selectedPillar || undefined,
        target_goal: goal,
      });
      setResult({ state: res.state, audit: res.audit });
    } catch (err: any) {
      setError(err.message || "Post generation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">Generate New Post</h1>
        <p className="text-sm text-slate-500 mt-1">
          Generate an editorial-grade post using Groq and the 20 hook formulas & V3 humanizer audit
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs">
        <form onSubmit={handleGenerate} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
                Content Pillar
              </label>
              <select
                value={selectedPillar}
                onChange={(e) => setSelectedPillar(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                {pillars.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.target_percentage}%)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
                Target Publication Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
              Topic / Core Argument (Optional)
            </label>
            <textarea
              rows={3}
              placeholder="Leave blank to use the rotation calendar's scheduled topic for this day, or enter a specific topic/angle..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-xl p-4 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-2">
              Post Objective
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { id: "comments", label: "Thoughtful Discussion" },
                { id: "saves", label: "Saves & Bookmarks" },
                { id: "practical_advice", label: "Practical Advice" },
                { id: "founder_insight", label: "Founder Insight" },
              ].map((obj) => (
                <button
                  type="button"
                  key={obj.id}
                  onClick={() => setGoal(obj.id)}
                  className={`p-3 rounded-xl border text-xs font-semibold text-center transition-all ${
                    goal === obj.id
                      ? "border-sky-500 bg-sky-50 text-sky-700 shadow-xs"
                      : "border-slate-200 text-slate-600 hover:border-slate-300"
                  }`}
                >
                  {obj.label}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center px-6 py-3 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 transition shadow-md shadow-sky-600/20 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Generating with Groq...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate Post Draft
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Generated Post Preview */}
      {result && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-6 animate-fade-in">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Generated Draft</span>
              <h2 className="text-lg font-bold text-slate-900 mt-0.5">{result.state.topic}</h2>
            </div>
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold ${
                result.audit.passed ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
              }`}
            >
              Audit: {result.audit.passed ? "PASSED" : "WARNINGS"}
            </span>
          </div>

          <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 whitespace-pre-line leading-relaxed">
            {result.state.draft_content}
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-slate-500 font-medium">
              Length: {result.state.draft_content?.length} characters • Formula: {result.state.hook_formula}
            </div>
            <button
              onClick={() => navigate(`/editor/${result.state.date}`)}
              className="inline-flex items-center px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 transition"
            >
              Open in Draft Editor <ArrowRight className="w-4 h-4 ml-1.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
