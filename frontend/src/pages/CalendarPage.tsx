import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Calendar, Filter, Sparkles, ArrowRight, CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import { api } from "../lib/api";
import { CalendarDay } from "../lib/types";

export const CalendarPage: React.FC = () => {
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPillar, setSelectedPillar] = useState<string>("all");
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null);

  useEffect(() => {
    api.getCalendar()
      .then((res) => {
        setDays(res.calendar);
        // Default select today
        const todayItem = res.calendar.find((d) => d.is_today);
        if (todayItem) setSelectedDay(todayItem);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredDays = days.filter((d) => {
    if (selectedPillar === "all") return true;
    return d.pillar_id === selectedPillar;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "published":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">Published</span>;
      case "approved":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-100 text-purple-800">Approved</span>;
      case "draft_saved":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-100 text-sky-800">Draft Ready</span>;
      case "failed":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-800">Failed</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">Planned</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">30-Day Content Calendar</h1>
          <p className="text-sm text-slate-500 mt-1">Rotating schedule across the 8 founder content pillars in Asia/Kolkata timezone</p>
        </div>
      </div>

      {/* Two Column Layout: Calendar Grid + Selected Day Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar Grid (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-bold text-slate-900 text-base flex items-center">
              <Calendar className="w-4 h-4 mr-2 text-sky-600" /> Schedule Grid
            </h2>
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-400">Total days:</span>
              <span className="font-semibold text-slate-700">{filteredDays.length}</span>
            </div>
          </div>

          {loading ? (
            <div className="py-24 flex justify-center">
              <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {filteredDays.map((d) => (
                <div
                  key={d.date}
                  onClick={() => setSelectedDay(d)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedDay?.date === d.date
                      ? "border-sky-500 bg-sky-50/40 ring-2 ring-sky-500/20 shadow-xs"
                      : d.is_today
                      ? "border-amber-300 bg-amber-50/20"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-900 flex items-center">
                      {d.date}
                      {d.is_today && (
                        <span className="ml-1.5 px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-amber-200 text-amber-900">
                          TODAY
                        </span>
                      )}
                    </span>
                    {getStatusBadge(d.status)}
                  </div>
                  <p className="text-[11px] font-semibold text-sky-700 line-clamp-1">{d.pillar_name}</p>
                  <p className="text-[11px] text-slate-600 line-clamp-2 mt-1 leading-snug">{d.topic}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selected Day Inspector */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="border-b border-slate-100 pb-4 mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Day Details</span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">{selectedDay?.date || "Select a date"}</h3>
              <p className="text-xs text-sky-700 font-semibold mt-0.5">{selectedDay?.pillar_name}</p>
            </div>

            {selectedDay ? (
              <div className="space-y-4 text-xs">
                <div>
                  <span className="text-slate-400 block font-medium">Topic Formulation:</span>
                  <p className="text-slate-800 font-medium mt-1 leading-relaxed">{selectedDay.topic}</p>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-slate-400 block text-[10px] font-semibold uppercase">Hook Formula</span>
                    <span className="text-slate-800 font-bold">{selectedDay.hook_formula}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-slate-400 block text-[10px] font-semibold uppercase">Founder Angle</span>
                    <span className="text-slate-800 font-bold">{selectedDay.founder_angle}</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 space-y-1">
                  <span className="text-slate-400 block text-[10px] font-semibold uppercase">Status</span>
                  <div className="flex items-center space-x-2">
                    {getStatusBadge(selectedDay.status)}
                    <span className="text-slate-600 font-medium">
                      {selectedDay.has_draft ? "Draft stored in GitHub outbox" : "Not yet generated"}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400 py-12 text-center">Click any day from the calendar to view its details.</p>
            )}
          </div>

          {selectedDay && (
            <div className="pt-6 border-t border-slate-100">
              <Link
                to={`/editor/${selectedDay.date}`}
                className="w-full inline-flex items-center justify-center px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 transition shadow-sm"
              >
                {selectedDay.has_draft ? "Open Draft Editor" : "Generate Draft for this Date"}
                <ArrowRight className="w-3.5 h-3.5 ml-2" />
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
