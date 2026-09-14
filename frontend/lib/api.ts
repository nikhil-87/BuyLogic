import {
  Scenario,
  ScenarioDetail,
  InventoryItem,
  PurchaseOrder,
  SystemMetrics,
  EvaluationReport
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {})
      },
      cache: "no-store"
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP Error ${res.status}: ${res.statusText}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`API fetch error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Scenarios
  getScenarios: () => fetchApi<Scenario[]>("/api/scenarios"),
  getScenarioDetail: (id: string) => fetchApi<ScenarioDetail>(`/api/scenarios/${id}`),
  
  // Decision Lifecycle
  approveDecision: (
    scenarioId: string,
    payload: {
      decision_id: string;
      approved: boolean;
      override_qty?: number;
      override_supplier_id?: string;
      feedback_notes?: string;
    }
  ) =>
    fetchApi<{ success: boolean; executed_orders: any[]; post_action_validation: any }>(
      `/api/scenarios/${scenarioId}/approve`,
      {
        method: "POST",
        body: JSON.stringify(payload)
      }
    ),

  rejectDecision: (
    scenarioId: string,
    payload: {
      decision_id: string;
      approved: boolean;
      feedback_notes?: string;
    }
  ) =>
    fetchApi<{ success: boolean; message: string }>(
      `/api/scenarios/${scenarioId}/reject`,
      {
        method: "POST",
        body: JSON.stringify(payload)
      }
    ),

  // Reset demo database to benchmark
  resetDatabase: () =>
    fetchApi<{ success: boolean; message: string }>("/api/scenarios/reset/database", {
      method: "POST"
    }),

  // Operational Data
  getInventory: () => fetchApi<InventoryItem[]>("/api/inventory"),
  getPurchaseOrders: (status?: string) =>
    fetchApi<PurchaseOrder[]>(`/api/purchase-orders${status ? `?status=${status}` : ""}`),
  getMetrics: () => fetchApi<SystemMetrics>("/api/metrics"),

  // Evaluation
  runEvaluation: () => fetchApi<EvaluationReport>("/api/evaluation/run"),

  // Streaming SSE endpoint
  getStreamUrl: (scenarioId: string) => `${API_BASE_URL}/api/scenarios/${scenarioId}/stream`
};
