"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Scenario, ScenarioDetail, SystemMetrics } from "@/types";
import { api } from "@/lib/api";
import MetricsBar from "@/components/MetricsBar";
import AgentWorkspace from "@/components/AgentWorkspace";
import {
  Bot,
  Sparkles,
  ArrowRight,
  Package,
  TrendingUp,
  AlertTriangle,
  Wallet,
  ShieldCheck,
  ChevronRight,
  Layers,
  Award,
  RefreshCw
} from "lucide-react";

export default function DashboardPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("scenario_1");
  const [scenarioDetail, setScenarioDetail] = useState<ScenarioDetail | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const [scens, mets] = await Promise.all([
        api.getScenarios(),
        api.getMetrics()
      ]);
      setScenarios(scens);
      setMetrics(mets);
      if (scens.length > 0 && !selectedScenarioId) {
        setSelectedScenarioId(scens[0].id);
      }
    } catch (err: any) {
      console.error("Error loading dashboard data:", err);
      setError("Unable to connect to backend server. Make sure the FastAPI service is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  const loadScenarioDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const detail = await api.getScenarioDetail(id);
      setScenarioDetail(detail);
    } catch (err: any) {
      console.error("Error loading scenario detail:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedScenarioId) {
      loadScenarioDetail(selectedScenarioId);
    }
  }, [selectedScenarioId]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Hero Section */}
      <div className="relative mb-8 p-8 rounded-3xl bg-gradient-to-br from-slate-900/90 via-[#111116] to-indigo-950/40 border border-slate-800 shadow-2xl overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-medium mb-3">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Next-Generation Autonomous Procurement</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-2 leading-tight">
            AI Purchasing Agent Platform
          </h1>
          <p className="text-sm sm:text-base text-slate-400 leading-relaxed mb-6">
            Investigates live inventory telemetry, demand anomalies, and multi-tier supplier constraints.
            Formulates mathematically optimal purchasing decisions with autonomous multi-constraint feedback verification.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/evaluation"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all"
            >
              <Award className="h-4 w-4" />
              <span>Run Evaluation Suite</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <button
              onClick={loadData}
              className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-medium border border-slate-700 transition-all cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Refresh Telemetry</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Bar */}
      <MetricsBar metrics={metrics} loading={loading} />

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={loadData}
            className="px-3 py-1 rounded-md bg-rose-500/20 hover:bg-rose-500/30 text-white font-medium"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Scenario Selector Tabs */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-indigo-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Procurement Scenarios
            </h2>
          </div>
          <span className="text-xs text-slate-400">Select a scenario to investigate</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {scenarios.map((sc) => {
            const isSelected = sc.id === selectedScenarioId;
            return (
              <button
                key={sc.id}
                onClick={() => setSelectedScenarioId(sc.id)}
                className={`text-left p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? "bg-slate-900 border-indigo-500 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500/40"
                    : "bg-slate-900/50 border-slate-800 hover:border-slate-700/80 hover:bg-slate-900/80"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                      Scenario {sc.scenario_number}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border ${
                        sc.status === "executed"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : sc.status === "decision_ready"
                          ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
                          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      }`}
                    >
                      {sc.status.replace("_", " ")}
                    </span>
                  </div>

                  <h3 className="text-xs font-bold text-white mb-1 line-clamp-1">{sc.title}</h3>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed mb-3">
                    {sc.description}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[11px]">
                  <span className="text-slate-400 font-medium truncate max-w-[120px]">
                    {sc.product?.name || sc.product_id}
                  </span>
                  <ChevronRight
                    className={`h-3.5 w-3.5 transition-transform ${
                      isSelected ? "text-indigo-400 translate-x-0.5" : "text-slate-400"
                    }`}
                  />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Selected Scenario Section */}
      {scenarioDetail && (
        <div className="space-y-6">
          {/* Scenario Context Data Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* 1. Target Product & Stock */}
            <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
              <div className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Package className="h-4 w-4 text-indigo-400" />
                <span>Product & Inventory Telemetry</span>
              </div>
              <h4 className="text-sm font-bold text-white mb-1">
                {scenarioDetail.product?.name}
              </h4>
              <p className="text-xs text-slate-400 mb-3">
                SKU: {scenarioDetail.product?.sku} • Category: {scenarioDetail.product?.category}
              </p>

              {scenarioDetail.inventories.length > 0 && (
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Current On-Hand Stock:</span>
                    <span className="font-bold text-white">
                      {scenarioDetail.inventories[0].current_stock} units
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Safety Stock Buffer:</span>
                    <span className="font-medium text-slate-300">
                      {scenarioDetail.inventories[0].safety_stock} units
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Shelf Storage Limit:</span>
                    <span className="font-medium text-slate-300">
                      {scenarioDetail.inventories[0].max_capacity} units
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-400">Free Storage Space:</span>
                    <span className="font-semibold text-emerald-400">
                      {scenarioDetail.inventories[0].available_capacity} slots
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 2. Demand Velocity & Open POs */}
            <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
              <div className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <TrendingUp className="h-4 w-4 text-sky-400" />
                <span>Demand Forecast & In-Transit POs</span>
              </div>

              {scenarioDetail.forecasts.length > 0 && (
                <div className="mb-3 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Forecasted Demand:</span>
                    <span className="font-bold text-white">
                      {scenarioDetail.forecasts[0].forecasted_qty} units / month
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Actual Run-Rate:</span>
                    <span
                      className={`font-bold ${
                        scenarioDetail.forecasts[0].trend === "spiking"
                          ? "text-amber-400"
                          : "text-white"
                      }`}
                    >
                      {scenarioDetail.forecasts[0].actual_run_rate_qty} units / month
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-400">Trend Status:</span>
                    <span
                      className={`font-mono text-[11px] uppercase ${
                        scenarioDetail.forecasts[0].trend === "spiking"
                          ? "text-rose-400 font-bold"
                          : "text-slate-300"
                      }`}
                    >
                      {scenarioDetail.forecasts[0].trend}
                    </span>
                  </div>
                </div>
              )}

              <div className="pt-2 border-t border-slate-800/80 text-xs">
                <span className="text-slate-400 block mb-1">Open Orders in Pipeline:</span>
                {scenarioDetail.open_pos.length === 0 ? (
                  <span className="text-slate-400 text-[11px]">No active POs in transit</span>
                ) : (
                  scenarioDetail.open_pos.map((po) => (
                    <div
                      key={po.id}
                      className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 flex items-center justify-between text-[11px]"
                    >
                      <div>
                        <span className="font-mono text-slate-300 font-medium">{po.id}</span>
                        <span className="text-slate-400 block text-[10px]">
                          {po.supplier_name}
                        </span>
                      </div>
                      <span className="font-mono font-bold text-indigo-300">
                        +{po.qty_ordered} units
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* 3. Budget & Supplier Terms */}
            <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
              <div className="flex items-center gap-2 mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <Wallet className="h-4 w-4 text-emerald-400" />
                <span>Node Budget & Supplier Matrix</span>
              </div>

              {scenarioDetail.budget && (
                <div className="mb-3 text-xs space-y-1">
                  <div className="flex justify-between py-1 border-b border-slate-800/80">
                    <span className="text-slate-400">Node Remaining Budget:</span>
                    <span className="font-bold text-emerald-400">
                      ${scenarioDetail.budget.remaining_budget.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-400">Total Budget Allocation:</span>
                    <span className="font-medium text-slate-300">
                      ${scenarioDetail.budget.total_budget.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              )}

              <div className="pt-2 border-t border-slate-800/80 text-xs">
                <span className="text-slate-400 block mb-1.5">Approved Suppliers:</span>
                <div className="space-y-1.5 max-h-28 overflow-y-auto">
                  {scenarioDetail.suppliers.map((sp) => (
                    <div
                      key={sp.id}
                      className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 flex items-center justify-between text-[11px]"
                    >
                      <div>
                        <span className="font-medium text-slate-200">{sp.supplier_name}</span>
                        {sp.is_preferred && (
                          <span className="ml-1.5 text-[9px] font-mono px-1 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                            Preferred
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-slate-200">
                          ${sp.unit_cost.toFixed(2)}
                        </span>
                        <span className="text-[10px] text-slate-400 block">
                          Stock: {sp.available_qty}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Agent Workspace */}
          <AgentWorkspace
            scenario={scenarioDetail}
            onRefresh={() => {
              loadData();
              if (selectedScenarioId) loadScenarioDetail(selectedScenarioId);
            }}
          />
        </div>
      )}
    </div>
  );
}
