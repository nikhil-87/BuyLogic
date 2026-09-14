"use client";

import React from "react";
import { SystemMetrics } from "@/types";
import { DollarSign, ShoppingBag, AlertTriangle, Wallet, ArrowUpRight } from "lucide-react";

interface MetricsBarProps {
  metrics: SystemMetrics | null;
  loading?: boolean;
}

export default function MetricsBar({ metrics, loading }: MetricsBarProps) {
  if (loading || !metrics) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-20 rounded-xl bg-slate-900/60 border border-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Committed PO Spend",
      value: `$${metrics.total_po_spend.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      sub: `${metrics.open_purchase_orders} active orders`,
      icon: DollarSign,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10 border-indigo-500/20"
    },
    {
      label: "Pending Scenarios",
      value: metrics.pending_scenarios.toString(),
      sub: "Requires agent investigation",
      icon: ShoppingBag,
      color: "text-sky-400",
      bg: "bg-sky-500/10 border-sky-500/20"
    },
    {
      label: "Stockout Hazards",
      value: metrics.stockout_hazards.toString(),
      sub: metrics.stockout_hazards > 0 ? "Under safety buffer!" : "All stocks above buffer",
      icon: AlertTriangle,
      color: metrics.stockout_hazards > 0 ? "text-amber-400" : "text-emerald-400",
      bg: metrics.stockout_hazards > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-emerald-500/10 border-emerald-500/20"
    },
    {
      label: "Procurement Liquidity",
      value: `$${metrics.remaining_budget.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
      sub: `${100 - metrics.budget_health_pct}% available of $${(metrics.total_budget / 1000).toFixed(0)}k`,
      icon: Wallet,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20"
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
      {cards.map((c, idx) => {
        const Icon = c.icon;
        return (
          <div
            key={idx}
            className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 hover:border-slate-700/80 transition-all flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">{c.label}</span>
              <div className={`p-1.5 rounded-lg border ${c.bg}`}>
                <Icon className={`h-3.5 w-3.5 ${c.color}`} />
              </div>
            </div>
            <div>
              <div className="text-xl font-bold tracking-tight text-white">{c.value}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">{c.sub}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
