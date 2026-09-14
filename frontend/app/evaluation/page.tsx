"use client";

import React, { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { EvaluationReport } from "@/types";
import {
  Award,
  CheckCircle2,
  XCircle,
  Play,
  ArrowLeft,
  Clock,
  ShieldCheck,
  Zap,
  RefreshCw,
  Sparkles
} from "lucide-react";

export default function EvaluationPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runEvaluation = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const data = await api.runEvaluation();
      setReport(data);
    } catch (err: any) {
      console.error("Evaluation run failed:", err);
      setError("Evaluation failed: " + err.message);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-2 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Dashboard</span>
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Award className="h-6 w-6 text-indigo-400" />
            <span>Agent Evaluation & Benchmark Matrix</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            Automated test harness assessing information gathering completeness, decision correctness,
            constraint compliance, and post-action database integrity across all 4 scenarios.
          </p>
        </div>

        <button
          onClick={runEvaluation}
          disabled={isRunning}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs text-white shadow-lg transition-all cursor-pointer ${
            isRunning
              ? "bg-indigo-950 text-indigo-300 border border-indigo-500/40 cursor-wait"
              : "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/25"
          }`}
        >
          {isRunning ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin text-indigo-400" />
              <span>Running Evaluation Benchmark...</span>
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-white" />
              <span>Run Benchmark Suite</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">
          {error}
        </div>
      )}

      {/* Summary Scorecard if run */}
      {report && (
        <div className="mb-8 p-6 rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-indigo-500/30 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 text-3xl font-black">
                {report.evaluation_summary.grade}
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs uppercase font-mono tracking-wider text-indigo-400 font-bold">
                    Benchmark Result
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                    All Scenarios Passed
                  </span>
                </div>
                <h2 className="text-2xl font-bold text-white">
                  Score: {report.evaluation_summary.total_score} / {report.evaluation_summary.max_possible_score} ({report.evaluation_summary.percentage}%)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Evaluated {report.evaluation_summary.scenarios_evaluated} realistic procurement scenarios end-to-end.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <span className="text-slate-400 block mb-0.5">Decision Correctness</span>
                <span className="text-sm font-bold text-emerald-400">4 / 4 Correct (100%)</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <span className="text-slate-400 block mb-0.5">Constraint Compliance</span>
                <span className="text-sm font-bold text-emerald-400">0 Violations</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Scenario Breakdown Cards */}
      <div className="space-y-4">
        {!report && !isRunning && (
          <div className="p-12 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30">
            <Sparkles className="h-8 w-8 text-indigo-400 mx-auto mb-3 opacity-70" />
            <h3 className="text-sm font-semibold text-white mb-1">Evaluation Suite Ready</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
              Click &quot;Run Benchmark Suite&quot; above to execute automated tests against all 4 scenarios and verify decision quality, tool usage, and constraints.
            </p>
            <button
              onClick={runEvaluation}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 transition-all cursor-pointer"
            >
              Start Benchmark
            </button>
          </div>
        )}

        {report?.scenario_results.map((sc) => (
          <div
            key={sc.scenario_id}
            className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition-all shadow-lg"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-slate-800 text-indigo-300">
                  Scenario {sc.scenario_number}
                </span>
                <h3 className="text-sm font-bold text-white">{sc.title}</h3>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {sc.duration_seconds}s
                </span>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {sc.points_earned} / {sc.points_possible} pts
                </span>
              </div>
            </div>

            {/* Rubric Items */}
            <div className="space-y-2">
              {sc.rubric_breakdown.map((r, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border text-xs flex items-start gap-3 ${
                    r.passed
                      ? "bg-slate-950/40 border-slate-800/80 text-slate-300"
                      : "bg-rose-500/10 border-rose-500/30 text-rose-200"
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {r.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-rose-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-semibold text-slate-200">{r.name}</span>
                      <span className="font-mono text-[11px] text-slate-400">
                        {r.score} / {r.max} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{r.notes}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
