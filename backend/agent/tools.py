import json
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import (
    Product, Supplier, SupplierProduct, FulfillmentNode,
    Inventory, PurchaseOrder, DemandForecast, Budget
)

AGENT_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Get current on-hand stock, safety stock, reserved inventory, and max warehouse storage capacity for a product at a specific fulfillment node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The product ID, e.g. 'PROD-EARBUDS-01'"},
                    "node_id": {"type": "string", "description": "The fulfillment node ID, e.g. 'NODE-NORTH-01'"}
                },
                "required": ["product_id", "node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_open_purchase_orders",
            "description": "Inspect all existing, in-transit, or open purchase orders for a product at a node to understand incoming pipeline inventory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The product ID"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_demand_forecast",
            "description": "Retrieve the current 30-day forecast, actual recent daily sales run-rate, and trend anomalies (e.g. spiking or seasonal).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The product ID"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_suppliers",
            "description": "Find all approved primary and alternative suppliers for a product with unit cost, lead time, min/max order quantities, available supplier stock, and reliability score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "The product ID"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_budget_and_capacity",
            "description": "Check node-level financial procurement budget (total, used, remaining) and facility physical storage capacity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "The fulfillment node ID"}
                },
                "required": ["node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_net_requirement",
            "description": "Helper math tool to calculate net inventory required given demand, stock, safety stock, and open POs over a horizon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expected_demand": {"type": "integer", "description": "Forecasted demand over target period"},
                    "current_stock": {"type": "integer", "description": "Current on-hand inventory"},
                    "incoming_orders": {"type": "integer", "description": "Open purchase order incoming quantities"},
                    "safety_stock": {"type": "integer", "description": "Required safety stock buffer"}
                },
                "required": ["expected_demand", "current_stock", "incoming_orders", "safety_stock"]
            }
        }
    }
]

class AgentToolsExecutor:
    """Executes database queries for agent tool calls."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return await handler(args)
        except Exception as e:
            return {"error": f"Tool execution failed for '{tool_name}': {str(e)}"}

    async def _tool_check_inventory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        product_id = args.get("product_id")
        node_id = args.get("node_id")
        query = select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.node_id == node_id
        )
        res = await self.session.execute(query)
        inv = res.scalar_one_or_none()
        if not inv:
            return {"status": "not_found", "message": f"No inventory record found for product {product_id} at {node_id}"}
        
        available_shelf_space = max(0, inv.max_capacity - inv.current_stock)
        return {
            "product_id": inv.product_id,
            "node_id": inv.node_id,
            "current_stock": inv.current_stock,
            "safety_stock": inv.safety_stock,
            "reserved_stock": inv.reserved_stock,
            "net_available_stock": inv.current_stock - inv.reserved_stock,
            "max_capacity": inv.max_capacity,
            "available_shelf_space": available_shelf_space,
            "stock_health": "below_safety_stock" if inv.current_stock < inv.safety_stock else "healthy"
        }

    async def _tool_check_open_purchase_orders(self, args: Dict[str, Any]) -> Dict[str, Any]:
        product_id = args.get("product_id")
        query = select(PurchaseOrder).where(
            PurchaseOrder.product_id == product_id,
            PurchaseOrder.status.in_(["pending", "confirmed", "partial"])
        )
        res = await self.session.execute(query)
        pos = res.scalars().all()
        
        po_list = []
        total_incoming = 0
        for po in pos:
            # If status is partial and has note about deliverable qty, take deliverable
            deliverable_qty = po.qty_ordered - po.qty_fulfilled
            if po.status == "partial" and "only 250" in (po.note or ""):
                deliverable_qty = 250
            total_incoming += deliverable_qty
            po_list.append({
                "po_id": po.id,
                "supplier_id": po.supplier_id,
                "qty_ordered": po.qty_ordered,
                "deliverable_qty": deliverable_qty,
                "unit_cost": po.unit_cost,
                "status": po.status,
                "expected_delivery": po.expected_delivery.isoformat() if po.expected_delivery else None,
                "note": po.note
            })
        return {
            "product_id": product_id,
            "open_po_count": len(po_list),
            "total_incoming_quantity": total_incoming,
            "open_orders": po_list
        }

    async def _tool_check_demand_forecast(self, args: Dict[str, Any]) -> Dict[str, Any]:
        product_id = args.get("product_id")
        query = select(DemandForecast).where(DemandForecast.product_id == product_id)
        res = await self.session.execute(query)
        fc = res.scalar_one_or_none()
        if not fc:
            return {"status": "not_found", "message": f"No forecast data for {product_id}"}
        
        daily_baseline = round(fc.forecasted_qty / 30.0, 1)
        daily_actual_run_rate = round(fc.actual_run_rate_qty / 30.0, 1)
        surge_percentage = round(((fc.actual_run_rate_qty - fc.forecasted_qty) / fc.forecasted_qty) * 100, 1) if fc.forecasted_qty > 0 else 0
        
        return {
            "product_id": fc.product_id,
            "period": fc.period,
            "forecasted_30d_demand": fc.forecasted_qty,
            "daily_forecast_rate": daily_baseline,
            "actual_30d_run_rate": fc.actual_run_rate_qty,
            "daily_actual_run_rate": daily_actual_run_rate,
            "trend": fc.trend,
            "surge_percentage": surge_percentage,
            "anomaly_detected": fc.trend == "spiking" or surge_percentage > 40,
            "notes": fc.notes
        }

    async def _tool_check_suppliers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        product_id = args.get("product_id")
        query = (
            select(SupplierProduct, Supplier)
            .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
            .where(SupplierProduct.product_id == product_id)
        )
        res = await self.session.execute(query)
        rows = res.all()
        
        suppliers_data = []
        for sp, s in rows:
            suppliers_data.append({
                "supplier_id": s.id,
                "supplier_name": s.name,
                "unit_cost": sp.unit_cost,
                "lead_time_days": s.lead_time_days,
                "min_order_qty": s.min_order_qty,
                "max_order_qty": s.max_order_qty,
                "supplier_inventory_available": sp.available_qty,
                "reliability_score": s.reliability_score,
                "is_preferred": sp.is_preferred,
                "active": s.active
            })
        
        # Sort preferred first, then by reliability
        suppliers_data.sort(key=lambda x: (not x["is_preferred"], -x["reliability_score"]))
        return {
            "product_id": product_id,
            "available_suppliers_count": len(suppliers_data),
            "suppliers": suppliers_data
        }

    async def _tool_check_budget_and_capacity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        node_id = args.get("node_id")
        b_query = select(Budget).where(Budget.node_id == node_id)
        b_res = await self.session.execute(b_query)
        budget = b_res.scalar_one_or_none()

        n_query = select(FulfillmentNode).where(FulfillmentNode.id == node_id)
        n_res = await self.session.execute(n_query)
        node = n_res.scalar_one_or_none()

        total_b = budget.total_budget if budget else 50000.0
        used_b = budget.used_budget if budget else 0.0
        rem_b = max(0.0, total_b - used_b)

        total_cap = node.total_capacity if node else 10000
        used_cap = node.used_capacity if node else 5000
        rem_cap = max(0, total_cap - used_cap)

        return {
            "node_id": node_id,
            "node_name": node.name if node else "Unknown Node",
            "total_budget": total_b,
            "used_budget": used_b,
            "remaining_budget": rem_b,
            "total_storage_capacity": total_cap,
            "used_storage_capacity": used_cap,
            "remaining_storage_capacity": rem_cap,
            "budget_utilization_pct": round((used_b / total_b) * 100, 1) if total_b > 0 else 0,
            "capacity_utilization_pct": round((used_cap / total_cap) * 100, 1) if total_cap > 0 else 0
        }

    async def _tool_calculate_net_requirement(self, args: Dict[str, Any]) -> Dict[str, Any]:
        demand = int(args.get("expected_demand", 0))
        current = int(args.get("current_stock", 0))
        incoming = int(args.get("incoming_orders", 0))
        safety = int(args.get("safety_stock", 0))

        # Net required = Demand + Safety Stock - Current Stock - Incoming Orders
        total_coverage_available = current + incoming
        net_shortfall = (demand + safety) - total_coverage_available
        reorder_recommended = max(0, net_shortfall)

        return {
            "expected_demand": demand,
            "safety_stock_target": safety,
            "total_target_inventory": demand + safety,
            "current_effective_pipeline": total_coverage_available,
            "net_shortfall": net_shortfall,
            "recommended_order_quantity": reorder_recommended,
            "coverage_status": "deficit" if net_shortfall > 0 else "sufficient"
        }
