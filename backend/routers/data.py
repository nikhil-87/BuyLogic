from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    Product, Supplier, SupplierProduct, Inventory,
    PurchaseOrder, DemandForecast, Budget, FulfillmentNode,
    Scenario
)
from backend.schemas import (
    ProductOut, SupplierOut, InventoryOut, PurchaseOrderOut,
    BudgetOut
)

router = APIRouter(prefix="/api", tags=["Data"])

@router.get("/products", response_model=List[ProductOut])
async def get_products(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Product))
    return res.scalars().all()

@router.get("/suppliers", response_model=List[SupplierOut])
async def get_suppliers(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Supplier))
    return res.scalars().all()

@router.get("/inventory")
async def get_inventory(db: AsyncSession = Depends(get_db)):
    query = (
        select(Inventory, Product, FulfillmentNode)
        .join(Product, Inventory.product_id == Product.id)
        .join(FulfillmentNode, Inventory.node_id == FulfillmentNode.id)
    )
    res = await db.execute(query)
    rows = res.all()

    items = []
    for inv, prod, node in rows:
        items.append({
            "id": inv.id,
            "product_id": inv.product_id,
            "product_name": prod.name,
            "sku": prod.sku,
            "category": prod.category,
            "node_id": inv.node_id,
            "node_name": node.name,
            "current_stock": inv.current_stock,
            "safety_stock": inv.safety_stock,
            "reserved_stock": inv.reserved_stock,
            "max_capacity": inv.max_capacity,
            "available_shelf_space": max(0, inv.max_capacity - inv.current_stock),
            "stock_health": "critical" if inv.current_stock < inv.safety_stock else ("low" if inv.current_stock < (inv.safety_stock * 1.5) else "healthy")
        })
    return items

@router.get("/purchase-orders", response_model=List[PurchaseOrderOut])
async def get_purchase_orders(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(PurchaseOrder, Product, Supplier)
        .join(Product, PurchaseOrder.product_id == Product.id)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .order_by(PurchaseOrder.created_at.desc())
    )
    if status:
        query = query.where(PurchaseOrder.status == status)

    res = await db.execute(query)
    rows = res.all()

    output = []
    for po, prod, sup in rows:
        output.append({
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
            "product_name": prod.name,
            "supplier_name": sup.name
        })
    return output

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    # Total PO spend
    po_res = await db.execute(select(func.sum(PurchaseOrder.total_cost)))
    total_spend = po_res.scalar() or 0.0

    # Open PO count
    open_po_res = await db.execute(
        select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status.in_(["pending", "confirmed", "partial"]))
    )
    open_pos = open_po_res.scalar() or 0

    # Pending scenarios count
    scen_res = await db.execute(select(func.count(Scenario.id)).where(Scenario.status != "executed"))
    pending_scenarios = scen_res.scalar() or 0

    # Stockout hazards (inventory < safety_stock)
    hazard_res = await db.execute(
        select(func.count(Inventory.id)).where(Inventory.current_stock < Inventory.safety_stock)
    )
    stockout_hazards = hazard_res.scalar() or 0

    # Budgets
    b_res = await db.execute(select(Budget))
    budgets = b_res.scalars().all()
    total_budget = sum(b.total_budget for b in budgets)
    used_budget = sum(b.used_budget for b in budgets)
    remaining_budget = max(0.0, total_budget - used_budget)

    return {
        "total_po_spend": total_spend,
        "open_purchase_orders": open_pos,
        "pending_scenarios": pending_scenarios,
        "stockout_hazards": stockout_hazards,
        "total_budget": total_budget,
        "used_budget": used_budget,
        "remaining_budget": remaining_budget,
        "budget_health_pct": round((used_budget / total_budget) * 100, 1) if total_budget > 0 else 0
    }
