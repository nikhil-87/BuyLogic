"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { PurchaseOrder } from "@/types";
import {
  ShoppingCart,
  ArrowLeft,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  Layers
} from "lucide-react";

export default function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await api.getPurchaseOrders();
      setOrders(data);
    } catch (err) {
      console.error("Failed to load POs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const filteredOrders = orders.filter((o) => {
    const matchesFilter = filter === "all" || o.status === filter;
    const matchesSearch =
      o.id.toLowerCase().includes(search.toLowerCase()) ||
      o.product_name?.toLowerCase().includes(search.toLowerCase()) ||
      o.supplier_name?.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

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
            <ShoppingCart className="h-6 w-6 text-indigo-400" />
            <span>Purchase Orders Ledger</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Auditable trail of all agent-generated, modified, and confirmed purchasing orders.
          </p>
        </div>

        <button
          onClick={loadOrders}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white border border-slate-700 transition-all cursor-pointer"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Orders</span>
        </button>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs">
          {["all", "confirmed", "partial", "pending"].map((st) => (
            <button
              key={st}
              onClick={() => setFilter(st)}
              className={`px-3 py-1.5 rounded-lg font-medium capitalize transition-all cursor-pointer ${
                filter === st
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search PO ID, item, supplier..."
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
                <th className="px-5 py-3">PO Number</th>
                <th className="px-5 py-3">Product / SKU</th>
                <th className="px-5 py-3">Vendor / Supplier</th>
                <th className="px-5 py-3 text-right">Quantity</th>
                <th className="px-5 py-3 text-right">Unit Cost</th>
                <th className="px-5 py-3 text-right">Total Committed</th>
                <th className="px-5 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                    Loading orders ledger...
                  </td>
                </tr>
              ) : filteredOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                    No purchase orders found.
                  </td>
                </tr>
              ) : (
                filteredOrders.map((po) => (
                  <tr key={po.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-5 py-3.5 font-mono font-bold text-white">
                      {po.id}
                      {po.note && (
                        <p className="text-[10px] text-slate-400 font-sans font-normal mt-0.5 line-clamp-1">
                          {po.note}
                        </p>
                      )}
                    </td>

                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-slate-200">{po.product_name || po.product_id}</div>
                      <span className="font-mono text-[10px] text-slate-400">{po.node_id}</span>
                    </td>

                    <td className="px-5 py-3.5">
                      <div className="text-slate-300 font-medium">{po.supplier_name || po.supplier_id}</div>
                    </td>

                    <td className="px-5 py-3.5 text-right font-mono font-bold text-indigo-300">
                      {po.qty_ordered.toLocaleString()}
                    </td>

                    <td className="px-5 py-3.5 text-right font-mono text-slate-400">
                      ${po.unit_cost.toFixed(2)}
                    </td>

                    <td className="px-5 py-3.5 text-right font-mono font-bold text-white">
                      ${po.total_cost.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </td>

                    <td className="px-5 py-3.5 text-right">
                      <span
                        className={`inline-flex items-center gap-1 text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border ${
                          po.status === "confirmed"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : po.status === "partial"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-slate-800 text-slate-300 border-slate-700"
                        }`}
                      >
                        {po.status === "confirmed" && <CheckCircle2 className="h-3 w-3" />}
                        {po.status === "partial" && <AlertCircle className="h-3 w-3" />}
                        <span>{po.status}</span>
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
