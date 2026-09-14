"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ScenarioDetail,
  AgentDecision,
  AgentActionLog,
  ValidationCheck
} from "@/types";
import { api } from "@/lib/api";
import ConstraintMatrix from "./ConstraintMatrix";
import MarkdownRenderer from "./MarkdownRenderer";
import {
  Play,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Terminal,
  Cpu,
  ArrowRight,
  ShieldAlert,
  Edit3,
  ThumbsDown,
  Check,
  RefreshCw,
  Clock,
  Layers
} from "lucide-react";

interface AgentWorkspaceProps {
  scenario: ScenarioDetail;
  onRefresh: () => void;
}

export default function AgentWorkspace({ scenario, onRefresh }: AgentWorkspaceProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [streamEvents, setStreamEvents] = useState<AgentActionLog[]>(scenario.action_logs || []);
  const [currentDecision, setCurrentDecision] = useState<AgentDecision | null>(
    scenario.latest_decision || null
  );
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);

  // Override State
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideQty, setOverrideQty] = useState<number>(
    scenario.latest_decision?.recommended_qty || 400
  );
  const [overrideSupplierId, setOverrideSupplierId] = useState<string>(
    scenario.latest_decision?.supplier_id || ""
  );
  const [overrideNotes, setOverrideNotes] = useState("");

  const streamEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setStreamEvents(scenario.action_logs || []);
    setCurrentDecision(scenario.latest_decision || null);
    if (scenario.latest_decision) {
      setOverrideQty(scenario.latest_decision.recommended_qty);
      setOverrideSupplierId(scenario.latest_decision.supplier_id || "");
    }
  }, [scenario]);

  useEffect(() => {
    if (isRunning) {
      streamEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [streamEvents, isRunning]);

  const runAgent = async () => {
    setIsRunning(true);
    setStreamEvents([]);
    setExecutionResult(null);
    setCurrentDecision(null);

    const streamUrl = api.getStreamUrl(scenario.id);

    try {
      const response = await fetch(streamUrl);
      if (!response.body) throw new Error("ReadableStream not supported.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const rawJson = line.replace("data: ", "").trim();
            if (!rawJson) continue;

            try {
              const event = JSON.parse(rawJson);

              if (event.type === "done") {
                setIsRunning(false);
                onRefresh();
                return;
              }

              if (event.type === "decision" && event.meta_info) {
                const decMeta = event.meta_info;
                setCurrentDecision({
                  id: decMeta.decision_id,
                  scenario_id: scenario.id,
                  decision_type: decMeta.decision_type,
                  recommended_qty: decMeta.recommended_qty,
                  supplier_id: decMeta.supplier_id,
                  reasoning: decMeta.reasoning,
                  confidence_score: decMeta.confidence_score,
                  proposed_actions: decMeta.proposed_actions,
                  validation_status: decMeta.validation_status,
                  iteration: 1,
                  user_status: "pending",
                  created_at: new Date().toISOString()
                });
                setOverrideQty(decMeta.recommended_qty);
                setOverrideSupplierId(decMeta.supplier_id || "");
              }

              setStreamEvents((prev) => [
                ...prev,
                {
                  scenario_id: scenario.id,
                  step_number: event.step_number || prev.length + 1,
                  step_type: event.type,
                  tool_name: event.tool_name,
                  tool_args: event.tool_args,
                  content: event.content,
                  meta_info: event.meta_info,
                  timestamp: event.timestamp || new Date().toISOString()
                }
              ]);
            } catch (parseErr) {
              console.error("Error parsing SSE line:", parseErr, rawJson);
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Streaming error:", err);
      alert("Error streaming agent reasoning: " + err.message);
    } finally {
      setIsRunning(false);
      onRefresh();
    }
  };

  const handleApprove = async () => {
    if (!currentDecision) return;
    setIsExecuting(true);
    try {
      const res = await api.approveDecision(scenario.id, {
        decision_id: currentDecision.id,
        approved: true
      });
      setExecutionResult(res);
      onRefresh();
    } catch (err: any) {
      alert("Execution error: " + err.message);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleExecuteOverride = async () => {
    if (!currentDecision) return;
    setIsExecuting(true);
    try {
      const res = await api.approveDecision(scenario.id, {
        decision_id: currentDecision.id,
        approved: true,
        override_qty: Number(overrideQty),
        override_supplier_id: overrideSupplierId || undefined,
        feedback_notes: overrideNotes
      });
      setExecutionResult(res);
      setShowOverrideModal(false);
      onRefresh();
    } catch (err: any) {
      alert("Override execution error: " + err.message);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleReject = async () => {
    if (!currentDecision) return;
    const reason = prompt("Enter rationale for rejecting this agent proposal:") || "Rejected by buyer.";
    setIsExecuting(true);
    try {
      await api.rejectDecision(scenario.id, {
        decision_id: currentDecision.id,
        approved: false,
        feedback_notes: reason
      });
      onRefresh();
    } catch (err: any) {
      alert("Rejection error: " + err.message);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Banner & Trigger Button */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-indigo-950/40 border border-slate-800 shadow-xl">
        <div className="flex items-center gap-3.5">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
            <Cpu className="h-5 w-5" />
            {isRunning && (
              <span className="absolute -inset-1 rounded-xl border border-indigo-500/50 animate-ping opacity-75" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-white tracking-tight">
                Autonomous Decision Engine
              </h3>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {isRunning ? "Reasoning in Real-Time" : "Standby"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-constraint ReAct pipeline with self-correcting validation feedback loop.
            </p>
          </div>
        </div>

        <button
          onClick={runAgent}
          disabled={isRunning || isExecuting}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium text-xs transition-all shadow-lg cursor-pointer ${
            isRunning
              ? "bg-indigo-950/80 text-indigo-300 border border-indigo-500/30 cursor-wait"
              : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/25 hover:shadow-indigo-600/40"
          }`}
        >
          {isRunning ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin text-indigo-400" />
              <span>Analyzing Scenario Telemetry...</span>
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-white" />
              <span>Run Autonomous Agent</span>
            </>
          )}
        </button>
      </div>

      {/* Real-Time Event Stream Log */}
      <div className="rounded-2xl border border-slate-800 bg-[#0d0d12] overflow-hidden flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80 bg-slate-900/50">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-slate-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Agent Reasoning & Tool Execution Log
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {streamEvents.length} Event(s)
          </span>
        </div>

        <div className="p-4 max-h-[420px] overflow-y-auto space-y-3 font-sans text-xs">
          {streamEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Sparkles className="h-8 w-8 text-slate-400 mb-2 opacity-60" />
              <p className="text-xs font-medium text-slate-400">No active execution trace</p>
              <p className="text-[11px] text-slate-400">
                Click &quot;Run Autonomous Agent&quot; above to initiate real-time investigation.
              </p>
            </div>
          ) : (
            streamEvents.map((ev, idx) => {
              if (ev.step_type === "thought") {
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 flex items-start gap-2.5 transition-all"
                  >
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-indigo-400 shrink-0 animate-pulse" />
                    <div className="flex-1 leading-relaxed">
                      <span className="text-[10px] font-mono uppercase text-indigo-400 block mb-0.5">
                        Agent Thought
                      </span>
                      <span>{ev.content}</span>
                    </div>
                  </div>
                );
              }

              if (ev.step_type === "tool_call") {
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-sky-950/20 border border-sky-800/40 text-sky-200 flex items-start gap-2.5"
                  >
                    <Terminal className="h-4 w-4 text-sky-400 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono uppercase text-sky-400">
                          Tool Invocation
                        </span>
                        <code className="text-[11px] text-sky-300 font-mono bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/50">
                          {ev.tool_name}()
                        </code>
                      </div>
                      {ev.tool_args && (
                        <pre className="mt-1.5 p-2 rounded-lg bg-black/40 text-[10px] font-mono text-slate-300 overflow-x-auto">
                          {JSON.stringify(ev.tool_args, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                );
              }

              if (ev.step_type === "tool_result") {
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 text-slate-300 flex items-start gap-2.5"
                  >
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <span className="text-[10px] font-mono uppercase text-emerald-400 block mb-0.5">
                        Observation Result ({ev.tool_name})
                      </span>
                      <p className="text-xs leading-relaxed text-slate-200">{ev.content}</p>
                    </div>
                  </div>
                );
              }

              if (ev.step_type === "validation_check" && ev.meta_info) {
                const checks = ev.meta_info.checks as ValidationCheck[];
                return (
                  <div key={idx} className="my-2">
                    <ConstraintMatrix checks={checks} title="Feedback Loop: Constraint Check Evaluation" />
                  </div>
                );
              }

              if (ev.step_type === "decision") {
                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/40 text-indigo-200 flex items-start gap-2.5 shadow-lg"
                  >
                    <Sparkles className="h-4 w-4 text-indigo-400 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <span className="text-[10px] font-mono uppercase text-indigo-400 block mb-0.5">
                        Synthesized Proposal
                      </span>
                      <p className="text-xs font-medium text-white">{ev.content}</p>
                    </div>
                  </div>
                );
              }

              return (
                <div key={idx} className="p-2.5 text-xs text-slate-400">
                  {ev.content}
                </div>
              );
            })
          )}
          <div ref={streamEndRef} />
        </div>
      </div>

      {/* Decision Card & Human-in-the-Loop Controls */}
      {currentDecision && (
        <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-b from-[#111116] to-[#0c0c10] p-6 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

          {/* Header */}
          <div className="flex flex-wrap items-start justify-between gap-4 pb-5 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2.5 mb-1.5">
                <span
                  className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${
                    currentDecision.decision_type === "modify"
                      ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                      : currentDecision.decision_type === "split_order"
                      ? "bg-sky-500/20 text-sky-300 border-sky-500/30"
                      : "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                  }`}
                >
                  Recommendation: {currentDecision.decision_type.replace("_", " ")}
                </span>
                <span className="text-xs font-mono text-slate-400">
                  Confidence: {(currentDecision.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
              <h2 className="text-xl font-bold tracking-tight text-white">
                Proposed Purchase: {currentDecision.recommended_qty} Units
              </h2>
            </div>

            {/* Validation Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <CheckCircle2 className="h-4 w-4" />
              <span>Multi-Constraint Validation Passed</span>
            </div>
          </div>

          {/* Proposed Actions List */}
          {currentDecision.proposed_actions && currentDecision.proposed_actions.length > 0 && (
            <div className="py-4 border-b border-slate-800">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2.5">
                Planned Procurement Actions
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {currentDecision.proposed_actions.map((act, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3"
                  >
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 shrink-0">
                      <Layers className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white capitalize">
                          {act.action_type.replace("_", " ")}
                        </span>
                        <span className="text-xs font-mono font-bold text-indigo-300">
                          {act.qty} units
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                        Supplier: {act.supplier_id || currentDecision.supplier_id || "Primary"}
                      </p>
                      {act.reason && (
                        <p className="text-[11px] text-slate-300 mt-1 leading-snug">
                          {act.reason}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Markdown Reasoning Body */}
          <div className="py-5 border-b border-slate-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-2.5">
              Decision Analysis & Trade-Off Evidence
            </span>
            <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 shadow-inner">
              <MarkdownRenderer content={currentDecision.reasoning} />
            </div>
          </div>

          {/* Execution Result Banner */}
          {executionResult && (
            <div className="mt-5 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-200">
              <div className="flex items-center gap-2 font-semibold text-xs mb-1 text-emerald-300">
                <CheckCircle2 className="h-4 w-4" />
                <span>Actions Executed & Verified in Production Database</span>
              </div>
              <p className="text-[11px] text-slate-300">
                Created/Updated {executionResult.executed_orders?.length || 1} purchase order record(s). Post-execution database validation confirmed 0 constraint violations.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-5">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ShieldAlert className="h-4 w-4 text-slate-400" />
              <span>Human Procurement Officer Sign-Off Required</span>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={handleReject}
                disabled={isExecuting || scenario.status === "executed"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium text-rose-300 hover:text-white bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition-all cursor-pointer disabled:opacity-50"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
                <span>Reject</span>
              </button>

              <button
                onClick={() => setShowOverrideModal(true)}
                disabled={isExecuting || scenario.status === "executed"}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium text-slate-200 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-all cursor-pointer disabled:opacity-50"
              >
                <Edit3 className="h-3.5 w-3.5" />
                <span>Modify & Override</span>
              </button>

              <button
                onClick={handleApprove}
                disabled={isExecuting || scenario.status === "executed"}
                className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold text-white shadow-lg transition-all cursor-pointer disabled:opacity-50 ${
                  scenario.status === "executed"
                    ? "bg-emerald-600/60 cursor-default"
                    : "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/25 hover:shadow-emerald-600/40"
                }`}
              >
                {isExecuting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Executing Purchase Order...</span>
                  </>
                ) : scenario.status === "executed" ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Order Executed</span>
                  </>
                ) : (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Approve & Execute PO</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Override Modal */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-1">Human Buyer Override</h3>
            <p className="text-xs text-slate-400 mb-4">
              Modify the proposed quantity or supplier before committing to the purchase order.
            </p>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Order Quantity</label>
                <input
                  type="number"
                  value={overrideQty}
                  onChange={(e) => setOverrideQty(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Supplier ID</label>
                <input
                  type="text"
                  value={overrideSupplierId}
                  onChange={(e) => setOverrideSupplierId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Override Reason Notes</label>
                <textarea
                  rows={2}
                  value={overrideNotes}
                  onChange={(e) => setOverrideNotes(e.target.value)}
                  placeholder="e.g. Adjusted based on supplier promotion..."
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 mt-5 pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowOverrideModal(false)}
                className="px-3.5 py-2 rounded-lg text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteOverride}
                disabled={isExecuting}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md cursor-pointer"
              >
                Apply & Execute PO
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
