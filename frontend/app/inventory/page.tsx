"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { InventoryItem } from "@/types";
import {
  Package,
  ArrowLeft,
  Search,
  AlertTriangle,
  CheckCircle2,
  Layers,
  Warehouse,
  RefreshCw
} from "lucide-react";

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const loadInventory = async () => {
    setLoading(true);
    try {
      const data = await api.getInventory();
      setItems(data);
    } catch (err) {
      console.error("Failed to load inventory:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInventory();
  }, []);

  const filteredItems = items.filter(
    (i) =>
      i.product_name?.toLowerCase().includes(search.toLowerCase()) ||
      i.sku?.toLowerCase().includes(search.toLowerCase()) ||
      i.node_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
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
            <Warehouse className="h-6 w-6 text-indigo-400" />
            <span>Fulfillment Node Inventory</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Real-time stock levels, dedicated SKU shelf limits, and buffer health across nodes.
          </p>
        </div>

        <button
          onClick={loadInventory}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white border border-slate-700 transition-all cursor-pointer"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Stock</span>
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="mb-6 flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search product, SKU, or distribution node..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/80 border-b border-slate-800 uppercase font-mono text-[10px] text-slate-400">
              <tr>
                <th className="px-5 py-3">Product / SKU</th>
                <th className="px-5 py-3">Fulfillment Node</th>
                <th className="px-5 py-3 text-right">Current On-Hand</th>
                <th className="px-5 py-3 text-right">Safety Stock Buffer</th>
                <th className="px-5 py-3">Shelf Capacity Utilization</th>
                <th className="px-5 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                    Loading live warehouse telemetry...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                    No matching inventory records found.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => {
                  const utilPct = Math.min(100, Math.round((item.current_stock / item.max_capacity) * 100));
                  const isCritical = item.current_stock < item.safety_stock;

                  return (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="font-semibold text-white">{item.product_name}</div>
                        <span className="font-mono text-[10px] text-slate-400">
                          {item.sku} • {item.category}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 text-slate-300">
                        <div>{item.node_name}</div>
                        <span className="font-mono text-[10px] text-slate-400">{item.node_id}</span>
                      </td>

                      <td className="px-5 py-3.5 text-right font-mono font-bold text-white text-sm">
                        {item.current_stock.toLocaleString()}
                      </td>

                      <td className="px-5 py-3.5 text-right font-mono text-slate-400">
                        {item.safety_stock.toLocaleString()}
                      </td>

                      <td className="px-5 py-3.5 min-w-[200px]">
                        <div className="flex items-center justify-between text-[10px] mb-1 font-mono text-slate-400">
                          <span>{item.current_stock} / {item.max_capacity} max</span>
                          <span>{utilPct}%</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              utilPct > 90
                                ? "bg-amber-500"
                                : utilPct > 50
                                ? "bg-indigo-500"
                                : "bg-sky-500"
                            }`}
                            style={{ width: `${utilPct}%` }}
                          />
                        </div>
                      </td>

                      <td className="px-5 py-3.5 text-right">
                        {isCritical ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            <AlertTriangle className="h-3 w-3" />
                            <span>Below Safety</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Optimal</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
