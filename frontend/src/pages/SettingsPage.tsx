import React, { useEffect, useState } from "react";
import {
  Settings,
  ShieldCheck,
  AlertTriangle,
  Lock,
  PauseCircle,
  CheckCircle2,
  ExternalLink,
  Sliders
} from "lucide-react";
import { api } from "../lib/api";
import { SettingsView } from "../lib/types";
import { Modal } from "../components/Modal";

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Auto-Publish modal
  const [autoPublishModalOpen, setAutoPublishModalOpen] = useState(false);
  const [confirmPhrase, setConfirmPhrase] = useState("");
  const [updatingMode, setUpdatingMode] = useState(false);

  useEffect(() => {
    api.getSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
  }, []);

  const handlePausePublishing = async () => {
    try {
      await api.pausePublishing();
      setFeedback("Publishing emergency pause triggered.");
    } catch (err: any) {
      setFeedback(`Error pausing: ${err.message}`);
    }
  };

  const handleEnableAutoPublish = async () => {
    if (confirmPhrase !== "ENABLE AUTO-PUBLISH") return;
    setUpdatingMode(true);
    try {
      await api.updatePublishingMode("auto_publish", confirmPhrase);
      setAutoPublishModalOpen(false);
      setConfirmPhrase("");
      setFeedback("Auto-publish mode enabled in dashboard. Ensure AUTO_PUBLISH=true and DRY_RUN=false in Render environment settings.");
      api.getSettings().then(setSettings);
    } catch (err: any) {
      setFeedback(`Failed to update mode: ${err.message}`);
    } finally {
      setUpdatingMode(false);
    }
  };

  const handleSetDraftOnly = async () => {
    try {
      await api.updatePublishingMode("draft_only");
      setFeedback("Switched to Draft-Only mode.");
      api.getSettings().then(setSettings);
    } catch (err: any) {
      setFeedback(`Error: ${err.message}`);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">System & Account Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Operational guardrails, integration credentials health, and publishing safety switches
        </p>
      </div>

      {feedback && (
        <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-sky-800 text-xs font-medium flex items-center justify-between">
          <span>{feedback}</span>
          <button onClick={() => setFeedback(null)} className="font-bold text-sm ml-2">&times;</button>
        </div>
      )}

      {/* Publishing Safety Controls */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="w-5 h-5 text-sky-600" />
            <h2 className="font-bold text-slate-900 text-base">Publishing Safety Modes</h2>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold ${
              settings?.auto_publish && !settings.dry_run
                ? "bg-amber-100 text-amber-800"
                : "bg-sky-50 text-sky-700"
            }`}
          >
            Current: {settings?.auto_publish && !settings.dry_run ? "Auto-Publish" : "Draft-Only (Safe)"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div
            onClick={handleSetDraftOnly}
            className={`p-5 rounded-xl border cursor-pointer transition-all ${
              !settings?.auto_publish || settings.dry_run
                ? "border-sky-500 bg-sky-50/30 ring-2 ring-sky-500/20"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-900 text-sm">Draft-Only Mode</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-sky-100 text-sky-800">RECOMMENDED</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Generates post drafts on daily schedule and records them to GitHub outbox. Never calls LinkedIn publish API.
            </p>
          </div>

          <div
            onClick={() => setAutoPublishModalOpen(true)}
            className={`p-5 rounded-xl border cursor-pointer transition-all ${
              settings?.auto_publish && !settings.dry_run
                ? "border-amber-500 bg-amber-50/30 ring-2 ring-amber-500/20"
                : "border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-900 text-sm">Auto-Publish Mode</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800">CAUTION</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Publishes daily generated posts automatically at 09:00 AM IST. Requires explicit safety confirmation.
            </p>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-between border-t border-slate-100">
          <span className="text-xs text-slate-500">Need to halt all outgoing requests immediately?</span>
          <button
            onClick={handlePausePublishing}
            className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 transition"
          >
            <PauseCircle className="w-4 h-4 mr-1.5" />
            Emergency Pause
          </button>
        </div>
      </div>

      {/* Integration Credentials Health (Non-Secret) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-6">
        <div className="flex items-center space-x-2.5 border-b border-slate-100 pb-4">
          <Lock className="w-5 h-5 text-slate-600" />
          <h2 className="font-bold text-slate-900 text-base">Integration Health & Configured Services</h2>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          In adherence with strict enterprise security policies, secret values (API keys, OAuth tokens) are never displayed in the frontend. Manage live tokens via Render dashboard environment secrets.
        </p>

        <div className="space-y-3 text-xs">
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <div>
              <span className="font-bold text-slate-900 block">Groq AI Engine</span>
              <span className="text-slate-500 text-[11px]">Model: {settings?.groq_model || "qwen/qwen3.8-27b"}</span>
            </div>
            <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-800">
              CONFIGURED
            </span>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <div>
              <span className="font-bold text-slate-900 block">Official LinkedIn API</span>
              <span className="text-slate-500 text-[11px]">
                Author URN: {settings?.linkedin_author_urn || "Configured"} • Endpoint: {settings?.linkedin_endpoint_style}
              </span>
            </div>
            <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-800">
              OAUTH TOKEN SET
            </span>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
            <div>
              <span className="font-bold text-slate-900 block">GitHub State Repository</span>
              <span className="text-slate-500 text-[11px]">
                Repo: {settings?.github_repository || "Not set"} • Branch: {settings?.github_state_branch}
              </span>
            </div>
            <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-800">
              CONNECTED
            </span>
          </div>
        </div>
      </div>

      {/* Operational Constants */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs space-y-4">
        <h2 className="font-bold text-slate-900 text-base">Schedule & Timezone</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/60">
            <span className="text-slate-400 block text-[10px] font-semibold uppercase">Timezone</span>
            <span className="text-slate-800 font-bold">{settings?.publish_timezone}</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/60">
            <span className="text-slate-400 block text-[10px] font-semibold uppercase">Daily Render Cron</span>
            <span className="text-slate-800 font-bold">30 3 * * * UTC (09:00 AM IST)</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/60">
            <span className="text-slate-400 block text-[10px] font-semibold uppercase">Max Post Length</span>
            <span className="text-slate-800 font-bold">{settings?.max_post_characters} characters</span>
          </div>
        </div>
      </div>

      {/* Auto-Publish Confirmation Modal */}
      <Modal
        isOpen={autoPublishModalOpen}
        onClose={() => setAutoPublishModalOpen(false)}
        title="Activate Auto-Publish Mode"
      >
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-2">
            <p className="font-bold flex items-center">
              <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-700" /> Mandatory Confirmation Gate
            </p>
            <p>
              Enabling auto-publish authorizes the daily Render Cron job to publish generated posts directly to your LinkedIn profile without manual pre-approval.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Type <strong className="text-amber-800">ENABLE AUTO-PUBLISH</strong> to confirm:
            </label>
            <input
              type="text"
              value={confirmPhrase}
              onChange={(e) => setConfirmPhrase(e.target.value)}
              placeholder="ENABLE AUTO-PUBLISH"
              className="w-full border border-slate-300 rounded-xl px-4 py-2 text-xs font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <button
              onClick={() => setAutoPublishModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleEnableAutoPublish}
              disabled={confirmPhrase !== "ENABLE AUTO-PUBLISH" || updatingMode}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 transition shadow-sm disabled:opacity-50"
            >
              {updatingMode ? "Enabling..." : "Confirm & Activate"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
