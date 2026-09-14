"use client";

import React from "react";
import { ValidationCheck } from "@/types";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";

interface ConstraintMatrixProps {
  checks: ValidationCheck[];
  title?: string;
}

export default function ConstraintMatrix({ checks, title = "Multi-Constraint Operational Validation" }: ConstraintMatrixProps) {
  if (!checks || checks.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-indigo-400" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">{title}</h4>
        </div>
        <span className="text-[11px] text-slate-400">
          {checks.filter((c) => c.passed).length}/{checks.length} Rules Passed
        </span>
      </div>

      <div className="space-y-2">
        {checks.map((check, idx) => {
          const isError = !check.passed;
          const isWarning = check.severity === "warning";

          return (
            <div
              key={idx}
              className={`p-2.5 rounded-lg border text-xs transition-all flex items-start gap-2.5 ${
                isError
                  ? "bg-rose-500/10 border-rose-500/30 text-rose-200"
                  : isWarning
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
                  : "bg-slate-950/60 border-slate-800/80 text-slate-300"
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isError ? (
                  <XCircle className="h-4 w-4 text-rose-400" />
                ) : isWarning ? (
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-200">{check.rule_name}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded font-mono uppercase tracking-wider ${
                      isError
                        ? "bg-rose-500/20 text-rose-300"
                        : isWarning
                        ? "bg-amber-500/20 text-amber-300"
                        : "bg-emerald-500/20 text-emerald-300"
                    }`}
                  >
                    {isError ? "Violated" : isWarning ? "Warning" : "Compliant"}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">{check.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
