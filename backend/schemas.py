import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    unit_price: float
    storage_units_per_item: float = 1.0
    description: Optional[str] = None

class ProductOut(ProductBase):
    class Config:
        from_attributes = True

class SupplierBase(BaseModel):
    id: str
    name: str
    lead_time_days: int
    min_order_qty: int
    max_order_qty: int
    reliability_score: float
    active: bool
    contact_email: Optional[str] = None

class SupplierOut(SupplierBase):
    class Config:
        from_attributes = True

class SupplierProductOut(BaseModel):
    id: int
    supplier_id: str
    product_id: str
    unit_cost: float
    available_qty: int
    is_preferred: bool
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True

class InventoryOut(BaseModel):
    id: int
    product_id: str
    node_id: str
    current_stock: int
    safety_stock: int
    reserved_stock: int
    max_capacity: int
    available_capacity: Optional[int] = None
    node_name: Optional[str] = None

    class Config:
        from_attributes = True

class PurchaseOrderOut(BaseModel):
    id: str
    product_id: str
    supplier_id: str
    node_id: str
    qty_ordered: int
    qty_fulfilled: int
    unit_cost: float
    total_cost: float
    status: str
    note: Optional[str] = None
    created_at: datetime.datetime
    expected_delivery: Optional[datetime.datetime] = None
    product_name: Optional[str] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True

class DemandForecastOut(BaseModel):
    id: int
    product_id: str
    node_id: str
    period: str
    forecasted_qty: int
    actual_run_rate_qty: int
    trend: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class BudgetOut(BaseModel):
    id: int
    node_id: str
    department: str
    total_budget: float
    used_budget: float
    remaining_budget: float
    period: str

    class Config:
        from_attributes = True

class ActionProposal(BaseModel):
    action_type: str  # create_po, modify_po, cancel_po, escalate, split_po
    product_id: str
    supplier_id: Optional[str] = None
    qty: int
    target_po_id: Optional[str] = None
    reason: Optional[str] = None
    estimated_cost: Optional[float] = None

class ValidationCheck(BaseModel):
    rule_name: str
    category: str  # budget, capacity, supplier_constraint, demand_coverage, reliability
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info
    details: Optional[Dict[str, Any]] = None

class AgentDecisionOut(BaseModel):
    id: str
    scenario_id: str
    decision_type: str  # accept, modify, reject, escalate, split_order
    recommended_qty: int
    supplier_id: Optional[str] = None
    reasoning: str
    confidence_score: float
    constraints_evaluated: Optional[Dict[str, Any]] = None
    proposed_actions: Optional[List[Dict[str, Any]]] = None
    validation_status: str
    validation_feedback: Optional[List[Dict[str, Any]]] = None
    iteration: int
    user_status: str
    user_override_reason: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class AgentActionLogOut(BaseModel):
    id: int
    scenario_id: str
    step_number: int
    step_type: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    content: str
    meta_info: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime

    class Config:
        from_attributes = True

class ScenarioOut(BaseModel):
    id: str
    scenario_number: int
    title: str
    scenario_type: str
    description: str
    product_id: str
    node_id: str
    initial_recommendation: Dict[str, Any]
    status: str
    created_at: datetime.datetime
    product: Optional[ProductOut] = None
    latest_decision: Optional[AgentDecisionOut] = None

    class Config:
        from_attributes = True

class ScenarioDetailOut(ScenarioOut):
    inventories: List[InventoryOut] = []
    suppliers: List[SupplierProductOut] = []
    forecasts: List[DemandForecastOut] = []
    open_pos: List[PurchaseOrderOut] = []
    budget: Optional[BudgetOut] = None
    action_logs: List[AgentActionLogOut] = []

class UserApprovalRequest(BaseModel):
    decision_id: str
    approved: bool
    override_qty: Optional[int] = None
    override_supplier_id: Optional[str] = None
    feedback_notes: Optional[str] = None

class RunAgentRequest(BaseModel):
    scenario_id: str
    force_fresh: bool = False
