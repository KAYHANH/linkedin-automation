import React, { useEffect, useState } from "react";
import { Compass, PieChart, ShieldCheck, Building2, User } from "lucide-react";
import { api } from "../lib/api";
import { StrategyData } from "../lib/types";

export const StrategyPage: React.FC = () => {
  const [strategy, setStrategy] = useState<StrategyData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStrategy()
      .then(setStrategy)
      .finally(() => setLoading(false));
  }, []);

  if (loading && !strategy) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">Content Strategy & Pillars</h1>
        <p className="text-sm text-slate-500 mt-1">
          Configured pillar distribution, brand voice profile, and verified company positioning facts
        </p>
      </div>

      {/* 8 Content Pillars Grid */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <h2 className="font-bold text-slate-900 text-base flex items-center">
            <PieChart className="w-4 h-4 mr-2 text-sky-600" /> 8 Content Pillars & Target Distribution
          </h2>
          <span className="text-xs font-semibold text-slate-500">30-Day Cycle Targets</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {strategy?.pillars.map((p) => (
            <div key={p.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-900">{p.name}</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800">
                    {p.target_percentage}%
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">{p.description}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-200/60 text-[10px] text-slate-400">
                Primary Goal: <strong className="text-slate-700 capitalize">{p.primary_goal}</strong>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Two Column Grid: Company Facts & Brand Profile */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Company Facts Isolation */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-4">
            <Building2 className="w-5 h-5 text-sky-600" />
            <h2 className="font-bold text-slate-900 text-base">Verified Company Facts (Anti-Hallucination)</h2>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            The content generator strictly isolates company-specific promotions to verified assertions. It is explicitly forbidden from inventing metrics, customer quotes, or fictitious features.
          </p>

          <div className="space-y-4 pt-2">
            {strategy && Object.entries(strategy.company_facts).map(([key, fact]) => (
              <div key={key} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-xs">{fact.name}</h3>
                  <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                    Strictly Verified
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed font-mono text-[11px]">{fact.positioning}</p>
                <div className="flex items-center space-x-4 text-[10px] text-slate-500 pt-1">
                  <span>Allowed Claims: <strong>{fact.allowed_claims_count}</strong></span>
                  <span>Strict Forbidden: <strong>{fact.strictly_forbidden_count}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Brand Voice Profile */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-4">
            <User className="w-5 h-5 text-indigo-600" />
            <h2 className="font-bold text-slate-900 text-base">Founder Voice Profile</h2>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Directly derived from the founder editorial guidelines: thoughtful, pragmatic Indian technology founder voice with natural sentence rhythm.
          </p>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs text-slate-700 leading-relaxed whitespace-pre-line max-h-80 overflow-y-auto">
            {strategy?.brand_profile_preview}
          </div>
        </div>
      </div>
    </div>
  );
};
