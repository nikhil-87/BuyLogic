"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Layers,
  Package,
  ShoppingCart,
  Award,
  RotateCcw,
  Sparkles,
  CheckCircle2
} from "lucide-react";
import { api } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const [resetting, setResetting] = useState(false);
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleReset = async () => {
    if (confirm("Reset database to initial pristine benchmark state?")) {
      setResetting(true);
      try {
        await api.resetDatabase();
        setResetSuccess(true);
        setTimeout(() => {
          setResetSuccess(false);
          window.location.reload();
        }, 800);
      } catch (err) {
        alert("Failed to reset database: " + err);
      } finally {
        setResetting(false);
      }
    }
  };

  const navItems = [
    { label: "Dashboard", href: "/", icon: Layers },
    { label: "Inventory", href: "/inventory", icon: Package },
    { label: "Purchase Orders", href: "/purchase-orders", icon: ShoppingCart },
    { label: "Agent Evaluation", href: "/evaluation", icon: Award }
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--border-subtle)] bg-[#09090b]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 group-hover:bg-indigo-600/30 transition-all">
              <Bot className="h-4 w-4" />
              <div className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-semibold tracking-tight text-slate-100">BuyLogic</span>
                  <span className="text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    AI
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 -mt-0.5">Purchasing Decision Platform</span>
              </div>
          </Link>
        </div>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? "bg-slate-800/80 text-white border border-slate-700 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-1.5 text-[11px] text-slate-400 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Engine Status: Connected</span>
          </div>

          <button
            onClick={handleReset}
            disabled={resetting}
            title="Reset to fresh demo dataset"
            className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white px-2.5 py-1.5 rounded-md border border-slate-800 hover:border-slate-700 bg-slate-900/60 hover:bg-slate-800 transition-all cursor-pointer"
          >
            {resetSuccess ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Reset!</span>
              </>
            ) : (
              <>
                <RotateCcw className={`h-3.5 w-3.5 text-slate-400 ${resetting ? "animate-spin" : ""}`} />
                <span className="hidden sm:inline">Reset Demo</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
