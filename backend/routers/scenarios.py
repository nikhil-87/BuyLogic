from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models import (
    Scenario, AgentDecision, AgentActionLog, Product,
    Supplier, SupplierProduct, Inventory, PurchaseOrder,
    DemandForecast, Budget, FulfillmentNode
)
from backend.schemas import (
    ScenarioOut, ScenarioDetailOut, AgentDecisionOut,
    UserApprovalRequest
)
from backend.agent.engine import PurchasingAgentEngine
from backend.seed import seed_data

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])

@router.get("", response_model=List[ScenarioOut])
async def list_scenarios(db: AsyncSession = Depends(get_db)):
    query = select(Scenario).order_by(Scenario.scenario_number)
    res = await db.execute(query)
    scenarios = res.scalars().all()

    output = []
    for s in scenarios:
        # Load product
        p_res = await db.execute(select(Product).where(Product.id == s.product_id))
        prod = p_res.scalar_one_or_none()

        # Load latest decision
        d_res = await db.execute(
            select(AgentDecision)
            .where(AgentDecision.scenario_id == s.id)
            .order_by(AgentDecision.created_at.desc())
        )
        dec = d_res.scalars().first()

        s_dict = {
            "id": s.id,
            "scenario_number": s.scenario_number,
            "title": s.title,
            "scenario_type": s.scenario_type,
            "description": s.description,
            "product_id": s.product_id,
            "node_id": s.node_id,
            "initial_recommendation": s.initial_recommendation,
            "status": s.status,
            "created_at": s.created_at,
            "product": prod,
            "latest_decision": dec
        }
        output.append(s_dict)
    return output

@router.get("/{scenario_id}", response_model=ScenarioDetailOut)
async def get_scenario_detail(scenario_id: str, db: AsyncSession = Depends(get_db)):
    s_res = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    scenario = s_res.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Load product
    p_res = await db.execute(select(Product).where(Product.id == scenario.product_id))
    product = p_res.scalar_one_or_none()

    # Load latest decision
    d_res = await db.execute(
        select(AgentDecision)
        .where(AgentDecision.scenario_id == scenario.id)
        .order_by(AgentDecision.created_at.desc())
    )
    latest_decision = d_res.scalars().first()

    # Load inventories
    inv_res = await db.execute(
        select(Inventory, FulfillmentNode)
        .join(FulfillmentNode, Inventory.node_id == FulfillmentNode.id)
        .where(Inventory.product_id == scenario.product_id)
    )
    inv_rows = inv_res.all()
    inventories = []
    for inv, node in inv_rows:
        inventories.append({
            "id": inv.id,
            "product_id": inv.product_id,
            "node_id": inv.node_id,
            "current_stock": inv.current_stock,
            "safety_stock": inv.safety_stock,
            "reserved_stock": inv.reserved_stock,
            "max_capacity": inv.max_capacity,
            "available_capacity": max(0, inv.max_capacity - inv.current_stock),
            "node_name": node.name
        })

    # Load suppliers
    sp_res = await db.execute(
        select(SupplierProduct, Supplier)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .where(SupplierProduct.product_id == scenario.product_id)
    )
    sp_rows = sp_res.all()
    suppliers = []
    for sp, sup in sp_rows:
        suppliers.append({
            "id": sp.id,
            "supplier_id": sp.supplier_id,
            "product_id": sp.product_id,
            "unit_cost": sp.unit_cost,
            "available_qty": sp.available_qty,
            "is_preferred": sp.is_preferred,
            "supplier_name": sup.name
        })

    # Load forecasts
    fc_res = await db.execute(select(DemandForecast).where(DemandForecast.product_id == scenario.product_id))
    forecasts = fc_res.scalars().all()

    # Load open POs
    po_res = await db.execute(
        select(PurchaseOrder, Supplier)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .where(PurchaseOrder.product_id == scenario.product_id)
    )
    po_rows = po_res.all()
    open_pos = []
    for po, sup in po_rows:
        open_pos.append({
            "id": po.id,
            "product_id": po.product_id,
            "supplier_id": po.supplier_id,
            "node_id": po.node_id,
            "qty_ordered": po.qty_ordered,
            "qty_fulfilled": po.qty_fulfilled,
            "unit_cost": po.unit_cost,
            "total_cost": po.total_cost,
            "status": po.status,
            "note": po.note,
            "created_at": po.created_at,
            "expected_delivery": po.expected_delivery,
            "product_name": product.name if product else None,
            "supplier_name": sup.name
        })

    # Load budget
    b_res = await db.execute(select(Budget).where(Budget.node_id == scenario.node_id))
    budget_row = b_res.scalar_one_or_none()
    budget_data = None
    if budget_row:
        budget_data = {
            "id": budget_row.id,
            "node_id": budget_row.node_id,
            "department": budget_row.department,
            "total_budget": budget_row.total_budget,
            "used_budget": budget_row.used_budget,
            "remaining_budget": budget_row.remaining_budget,
            "period": budget_row.period
        }

    # Load action logs
    log_res = await db.execute(
        select(AgentActionLog)
        .where(AgentActionLog.scenario_id == scenario.id)
        .order_by(AgentActionLog.step_number)
    )
    logs = log_res.scalars().all()

    return {
        "id": scenario.id,
        "scenario_number": scenario.scenario_number,
        "title": scenario.title,
        "scenario_type": scenario.scenario_type,
        "description": scenario.description,
        "product_id": scenario.product_id,
        "node_id": scenario.node_id,
        "initial_recommendation": scenario.initial_recommendation,
        "status": scenario.status,
        "created_at": scenario.created_at,
        "product": product,
        "latest_decision": latest_decision,
        "inventories": inventories,
        "suppliers": suppliers,
        "forecasts": forecasts,
        "open_pos": open_pos,
        "budget": budget_data,
        "action_logs": logs
    }

@router.get("/{scenario_id}/stream")
async def stream_agent(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Server-Sent Events endpoint streaming real-time agent reasoning steps."""
    engine = PurchasingAgentEngine(db)
    return StreamingResponse(
        engine.run_agent_stream(scenario_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/{scenario_id}/approve")
async def approve_decision(
    scenario_id: str,
    payload: UserApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """Approves agent decision, creating/modifying POs and executing post-action verification."""
    engine = PurchasingAgentEngine(db)
    try:
        res = await engine.execute_approved_decision(
            decision_id=payload.decision_id,
            user_override_qty=payload.override_qty,
            user_override_supplier_id=payload.override_supplier_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{scenario_id}/reject")
async def reject_decision(
    scenario_id: str,
    payload: UserApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """Rejects decision with feedback reason."""
    d_res = await db.execute(select(AgentDecision).where(AgentDecision.id == payload.decision_id))
    dec = d_res.scalar_one_or_none()
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")

    dec.user_status = "rejected"
    dec.user_override_reason = payload.feedback_notes or "Rejected by human procurement officer."

    s_res = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    s = s_res.scalar_one_or_none()
    if s:
        s.status = "rejected"

    await db.commit()
    return {"success": True, "message": "Decision marked as rejected", "decision_id": dec.id}

@router.post("/reset/database")
async def reset_demo_database():
    """Resets entire database to the original fresh benchmark state."""
    await seed_data()
    return {"success": True, "message": "Database reset to benchmark state"}
