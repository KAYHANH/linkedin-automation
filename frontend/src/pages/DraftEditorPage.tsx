import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Save,
  ShieldCheck,
  Send,
  Trash2,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ExternalLink
} from "lucide-react";
import { api } from "../lib/api";
import { AuditResult, DailyPostState } from "../lib/types";
import { Modal } from "../components/Modal";

export const DraftEditorPage: React.FC = () => {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();

  const [state, setState] = useState<DailyPostState | null>(null);
  const [content, setContent] = useState("");
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [approving, setApproving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Modals
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [discardModalOpen, setDiscardModalOpen] = useState(false);

  const loadDraft = () => {
    if (!date) return;
    setLoading(true);
    api.getPostDetail(date)
      .then((res) => {
        setState(res.state);
        setContent(res.state.draft_content || "");
        if (res.state.audit_summary) {
          setAudit(res.state.audit_summary);
        } else if (res.state.draft_content) {
          runAudit(res.state.draft_content);
        }
      })
      .catch((err) => {
        setFeedback({ type: "error", text: err.message || "Failed to load draft." });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDraft();
  }, [date]);

  const runAudit = async (textToAudit: string) => {
    if (!date) return;
    setAuditing(true);
    try {
      const res = await api.auditPost(date, textToAudit);
      setAudit(res);
    } catch {
      // Ignored
    } finally {
      setAuditing(false);
    }
  };

  const handleSave = async () => {
    if (!date) return;
    setSaving(true);
    setFeedback(null);
    try {
      const res = await api.updatePost(date, content);
      setState(res.state);
      setAudit(res.audit);
      setFeedback({ type: "success", text: "Draft changes saved to GitHub state!" });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!date) return;
    setApproving(true);
    setFeedback(null);
    try {
      const res = await api.approvePost(date);
      setState(res.state);
      setFeedback({ type: "success", text: "Draft approved! Cryptographically bound to current content hash." });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setApproving(false);
    }
  };

  const handlePublishConfirmed = async () => {
    if (!date) return;
    setPublishing(true);
    setFeedback(null);
    setPublishModalOpen(false);
    try {
      const res = await api.publishPost(date);
      setState(res.state);
      setFeedback({ type: "success", text: `Published successfully! LinkedIn Post ID: ${res.post_id}` });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Publication failed or was blocked by safety guardrails." });
    } finally {
      setPublishing(false);
    }
  };

  const handleDiscardConfirmed = async () => {
    if (!date) return;
    setDiscardModalOpen(false);
    try {
      await api.discardPost(date);
      navigate("/drafts");
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    }
  };

  const maxChars = 2200;
  const charCount = content.length;
  const isOverLimit = charCount > maxChars;

  if (loading && !state) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-sky-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs text-slate-500 font-medium mb-1">
            <span>{state?.date}</span>
            <span>•</span>
            <span className="font-semibold text-sky-700">{state?.pillar_name}</span>
            <span>•</span>
            <span>Hook: {state?.hook_formula}</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">{state?.topic}</h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 shadow-xs transition"
          >
            <Save className="w-3.5 h-3.5 mr-1.5" />
            {saving ? "Saving..." : "Save Changes"}
          </button>

          <button
            onClick={handleApprove}
            disabled={approving || state?.draft_status === "approved"}
            className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition disabled:opacity-50"
          >
            <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
            {state?.draft_status === "approved" ? "Approved" : "Approve Draft"}
          </button>

          <button
            onClick={() => setPublishModalOpen(true)}
            disabled={publishing || state?.publication_status === "published"}
            className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold bg-sky-600 text-white hover:bg-sky-500 transition shadow-sm disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5 mr-1.5" />
            {state?.publication_status === "published" ? "Published" : "Publish Now"}
          </button>

          <button
            onClick={() => setDiscardModalOpen(true)}
            className="p-2 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
            title="Discard Draft"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-xl text-xs font-medium flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
              : "bg-rose-50 border border-rose-200 text-rose-800"
          }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} className="font-bold text-sm ml-2">&times;</button>
        </div>
      )}

      {/* Side-by-side Editor & LinkedIn Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Text Editor */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Post Draft Editor</span>
              <div className="flex items-center space-x-2 text-xs">
                <span className={`font-semibold ${isOverLimit ? "text-rose-600 font-bold" : "text-slate-600"}`}>
                  {charCount}
                </span>
                <span className="text-slate-400">/ {maxChars} characters</span>
              </div>
            </div>

            <textarea
              rows={16}
              value={content}
              onChange={(e) => {
                setContent(e.target.value);
                runAudit(e.target.value);
              }}
              className="w-full bg-slate-50/50 border border-slate-200 rounded-xl p-4 text-xs font-mono text-slate-800 leading-relaxed focus:outline-none focus:ring-2 focus:ring-sky-500 transition resize-none"
              placeholder="Post text here..."
            />
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Formula: <strong>{state?.hook_formula}</strong></span>
            <span>Angle: <strong>{state?.founder_angle}</strong></span>
          </div>
        </div>

        {/* Right: LinkedIn Live Preview */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">LinkedIn Feed Preview</span>
            <span className="text-[11px] font-medium text-slate-400">Personal Post Mockup</span>
          </div>

          <div className="border border-slate-200 rounded-xl p-5 bg-white shadow-xs">
            {/* Author bar */}
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold text-sm">
                F
              </div>
              <div>
                <p className="text-xs font-bold text-slate-900 leading-tight">Founder</p>
                <p className="text-[10px] text-slate-500">Technology Founder • 1st</p>
                <p className="text-[10px] text-slate-400 flex items-center">Just now • 🌐</p>
              </div>
            </div>

            {/* Post Content */}
            <div className="text-xs text-slate-900 leading-relaxed whitespace-pre-line font-sans">
              {content || "No post content entered."}
            </div>

            {/* Social mock buttons */}
            <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-around text-xs text-slate-500 font-semibold">
              <span className="cursor-default hover:text-sky-600">👍 Like</span>
              <span className="cursor-default hover:text-sky-600">💬 Comment</span>
              <span className="cursor-default hover:text-sky-600">🔁 Repost</span>
              <span className="cursor-default hover:text-sky-600">📤 Send</span>
            </div>
          </div>
        </div>
      </div>

      {/* V3 Editorial Safety & Quality Audit Panel */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="w-5 h-5 text-sky-600" />
            <h3 className="font-bold text-slate-900 text-base">V3 Humanizer & Editorial Quality Audit</h3>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-bold ${
              audit?.passed ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
            }`}
          >
            {audit?.passed ? "AUDIT PASSED" : "BLOCKERS DETECTED"}
          </span>
        </div>

        {audit ? (
          <div className="space-y-4">
            {audit.blockers.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-rose-600">Blockers (Must Resolve)</span>
                {audit.blockers.map((b, i) => (
                  <div key={i} className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600" />
                    <div>
                      <strong className="block font-semibold">[{b.rule}]</strong>
                      <span>{b.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {audit.warnings.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-600">Warnings (Advisory)</span>
                {audit.warnings.map((w, i) => (
                  <div key={i} className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600" />
                    <div>
                      <strong className="block font-semibold">[{w.rule}]</strong>
                      <span>{w.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {audit.blockers.length === 0 && audit.warnings.length === 0 && (
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2 font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Zero AI tells detected! Natural tone, paragraph rhythm, vocabulary density, and character constraints all validated.</span>
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-slate-400 py-4 text-center">Auditing content...</div>
        )}
      </div>

      {/* Publish Confirmation Modal */}
      <Modal
        isOpen={publishModalOpen}
        onClose={() => setPublishModalOpen(false)}
        title="Confirm Live LinkedIn Publication"
      >
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs">
            <p className="font-bold flex items-center mb-1">
              <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-700" /> Live Publication Notice
            </p>
            <p>
              This action will publish this exact content immediately to your personal LinkedIn profile using the official Posts API.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
            <p className="text-slate-500 font-medium">Target Author URN:</p>
            <p className="font-mono text-slate-800 font-semibold">{state?.date} • {charCount} chars</p>
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <button
              onClick={() => setPublishModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition"
            >
              Cancel
            </button>
            <button
              onClick={handlePublishConfirmed}
              disabled={publishing}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 transition shadow-sm"
            >
              {publishing ? "Publishing..." : "Yes, Publish to LinkedIn"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Discard Confirmation Modal */}
      <Modal
        isOpen={discardModalOpen}
        onClose={() => setDiscardModalOpen(false)}
        title="Discard Draft"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600">
            Are you sure you want to discard this draft? The draft content will be reset in your GitHub outbox.
          </p>
          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <button
              onClick={() => setDiscardModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleDiscardConfirmed}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 transition"
            >
              Discard Draft
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
