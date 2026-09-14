export interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  unit_price: number;
  storage_units_per_item: number;
  description?: string;
}

export interface Supplier {
  id: string;
  name: string;
  lead_time_days: number;
  min_order_qty: number;
  max_order_qty: number;
  reliability_score: number;
  active: boolean;
  contact_email?: string;
}

export interface SupplierProduct {
  id: number;
  supplier_id: string;
  product_id: string;
  unit_cost: number;
  available_qty: number;
  is_preferred: boolean;
  supplier_name?: string;
}

export interface InventoryItem {
  id: number;
  product_id: string;
  product_name?: string;
  sku?: string;
  category?: string;
  node_id: string;
  node_name?: string;
  current_stock: number;
  safety_stock: number;
  reserved_stock: number;
  max_capacity: number;
  available_shelf_space?: number;
  available_capacity?: number;
  stock_health?: "critical" | "low" | "healthy";
}

export interface PurchaseOrder {
  id: string;
  product_id: string;
  supplier_id: string;
  node_id: string;
  qty_ordered: number;
  qty_fulfilled: number;
  unit_cost: number;
  total_cost: number;
  status: "pending" | "confirmed" | "partial" | "fulfilled" | "cancelled";
  note?: string;
  created_at: string;
  expected_delivery?: string;
  product_name?: string;
  supplier_name?: string;
}

export interface DemandForecast {
  id: number;
  product_id: string;
  node_id: string;
  period: string;
  forecasted_qty: number;
  actual_run_rate_qty: number;
  trend: string;
  notes?: string;
}

export interface Budget {
  id: number;
  node_id: string;
  department: string;
  total_budget: number;
  used_budget: number;
  remaining_budget: number;
  period: string;
}

export interface ProposedAction {
  action_type: "create_po" | "modify_po" | "cancel_po" | "split_po" | "escalate";
  product_id: string;
  supplier_id?: string;
  qty: number;
  target_po_id?: string;
  reason?: string;
  estimated_cost?: number;
}

export interface ValidationCheck {
  rule_name: string;
  category: "financial" | "spatial" | "supplier_constraint" | "demand_coverage" | "reliability";
  passed: boolean;
  severity: "error" | "warning" | "info";
  message: string;
  details?: Record<string, any>;
}

export interface ValidationReport {
  passed: boolean;
  status: "passed" | "warning" | "failed";
  checks: ValidationCheck[];
  total_checks: number;
  passed_checks_count: number;
  failed_checks_count: number;
  warnings_count: number;
  feedback_for_agent: string;
}

export interface AgentDecision {
  id: string;
  scenario_id: string;
  decision_type: "accept" | "modify" | "reject" | "escalate" | "split_order";
  recommended_qty: number;
  supplier_id?: string;
  reasoning: string;
  confidence_score: number;
  constraints_evaluated?: Record<string, any>;
  proposed_actions?: ProposedAction[];
  validation_status: "passed" | "warning" | "failed";
  validation_feedback?: ValidationCheck[];
  iteration: number;
  user_status: "pending" | "approved" | "modified" | "rejected";
  user_override_reason?: string;
  created_at: string;
}

export interface AgentActionLog {
  id?: number;
  scenario_id: string;
  step_number: number;
  step_type: "thought" | "tool_call" | "tool_result" | "validation_check" | "decision" | "execution";
  tool_name?: string;
  tool_args?: Record<string, any>;
  content: string;
  meta_info?: Record<string, any>;
  timestamp: string;
}

export interface Scenario {
  id: string;
  scenario_number: number;
  title: string;
  scenario_type: "recommendation_review" | "supplier_shortfall" | "demand_spike" | "purchasing_constraint";
  description: string;
  product_id: string;
  node_id: string;
  initial_recommendation: Record<string, any>;
  status: "pending_review" | "analyzing" | "decision_ready" | "approved" | "modified" | "rejected" | "executed";
  created_at: string;
  product?: Product;
  latest_decision?: AgentDecision;
}

export interface ScenarioDetail extends Scenario {
  inventories: InventoryItem[];
  suppliers: SupplierProduct[];
  forecasts: DemandForecast[];
  open_pos: PurchaseOrder[];
  budget?: Budget;
  action_logs: AgentActionLog[];
}

export interface SystemMetrics {
  total_po_spend: number;
  open_purchase_orders: number;
  pending_scenarios: number;
  stockout_hazards: number;
  total_budget: number;
  used_budget: number;
  remaining_budget: number;
  budget_health_pct: number;
}

export interface EvaluationRubricItem {
  name: string;
  passed: boolean;
  score: number;
  max: number;
  notes: string;
}

export interface ScenarioEvaluationResult {
  scenario_id: string;
  scenario_number: number;
  title: string;
  duration_seconds: number;
  points_earned: number;
  points_possible: number;
  status: "passed" | "partial" | "failed";
  decision_summary: {
    decision_type: string;
    recommended_qty: number;
    supplier_id?: string;
    validation_status: string;
  };
  rubric_breakdown: EvaluationRubricItem[];
}

export interface EvaluationReport {
  evaluation_summary: {
    total_score: number;
    max_possible_score: number;
    percentage: number;
    grade: string;
    scenarios_evaluated: number;
    all_passed: boolean;
  };
  scenario_results: ScenarioEvaluationResult[];
}
