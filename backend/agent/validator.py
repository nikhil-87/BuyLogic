from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import (
    Product, Supplier, SupplierProduct, FulfillmentNode,
    Inventory, PurchaseOrder, DemandForecast, Budget
)

class DecisionValidator:
    """
    Validates agent proposed purchasing decisions against operational,
    financial, spatial, and supplier constraints.
    Provides actionable structured feedback for the agent's feedback loop.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_decision(
        self,
        scenario_id: str,
        product_id: str,
        node_id: str,
        decision_type: str,
        recommended_qty: int,
        supplier_id: Optional[str],
        proposed_actions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Runs comprehensive constraint validation on a proposed purchasing decision.
        """
        checks: List[Dict[str, Any]] = []
        is_passed = True
        has_warnings = False
        feedback_notes = []

        # Fetch product
        p_res = await self.session.execute(select(Product).where(Product.id == product_id))
        product = p_res.scalar_one_or_none()

        # Fetch inventory
        inv_res = await self.session.execute(
            select(Inventory).where(Inventory.product_id == product_id, Inventory.node_id == node_id)
        )
        inventory = inv_res.scalar_one_or_none()

        # Fetch budget
        b_res = await self.session.execute(select(Budget).where(Budget.node_id == node_id))
        budget = b_res.scalar_one_or_none()

        # Fetch node
        n_res = await self.session.execute(select(FulfillmentNode).where(FulfillmentNode.id == node_id))
        node = n_res.scalar_one_or_none()

        # Fetch forecast
        fc_res = await self.session.execute(select(DemandForecast).where(DemandForecast.product_id == product_id))
        forecast = fc_res.scalar_one_or_none()

        # Fetch open POs
        po_res = await self.session.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.product_id == product_id,
                PurchaseOrder.status.in_(["pending", "confirmed", "partial"])
            )
        )
        open_pos = po_res.scalars().all()
        current_incoming = sum(
            po.qty_ordered - po.qty_fulfilled if po.status != "partial" else 250
            for po in open_pos
        )

        # Determine target actions and total cost
        actions = proposed_actions or []
        if not actions and recommended_qty > 0 and supplier_id:
            actions = [{
                "action_type": "create_po",
                "product_id": product_id,
                "supplier_id": supplier_id,
                "qty": recommended_qty
            }]

        total_new_po_cost = 0.0
        total_new_qty = 0

        for act in actions:
            act_qty = int(act.get("qty", 0))
            act_sup_id = act.get("supplier_id") or supplier_id
            
            # Fetch supplier-product cost
            sp_res = await self.session.execute(
                select(SupplierProduct).where(
                    SupplierProduct.product_id == product_id,
                    SupplierProduct.supplier_id == act_sup_id
                )
            )
            sp = sp_res.scalar_one_or_none()
            unit_cost = sp.unit_cost if sp else (product.unit_price if product else 20.0)
            total_new_po_cost += act_qty * unit_cost
            total_new_qty += act_qty

        # -------------------------------------------------------------
        # CHECK 1: Budget Constraint
        # -------------------------------------------------------------
        rem_budget = budget.remaining_budget if budget else 50000.0
        if total_new_po_cost > rem_budget:
            is_passed = False
            over_by = total_new_po_cost - rem_budget
            checks.append({
                "rule_name": "Budget Compliance",
                "category": "financial",
                "passed": False,
                "severity": "error",
                "message": f"Proposed order cost (${total_new_po_cost:,.2f}) exceeds remaining budget of ${rem_budget:,.2f} by ${over_by:,.2f}.",
                "details": {
                    "total_cost": total_new_po_cost,
                    "remaining_budget": rem_budget,
                    "deficit": over_by,
                    "max_affordable_qty": int(rem_budget / (total_new_po_cost / total_new_qty)) if total_new_qty > 0 else 0
                }
            })
            feedback_notes.append(
                f"BUDGET VIOLATION: Reduce total purchase cost to below ${rem_budget:,.2f}."
            )
        else:
            checks.append({
                "rule_name": "Budget Compliance",
                "category": "financial",
                "passed": True,
                "severity": "info",
                "message": f"Approved: Total spend (${total_new_po_cost:,.2f}) is within remaining budget (${rem_budget:,.2f}).",
                "details": {"remaining_after_purchase": rem_budget - total_new_po_cost}
            })

        # -------------------------------------------------------------
        # CHECK 2: Warehouse Shelf & Storage Capacity Constraint
        # -------------------------------------------------------------
        current_stock = inventory.current_stock if inventory else 0
        sku_max_cap = inventory.max_capacity if inventory else 1000
        net_after_delivery = current_stock + current_incoming + total_new_qty

        # Check SKU shelf limit
        if net_after_delivery > sku_max_cap:
            is_passed = False
            overflow = net_after_delivery - sku_max_cap
            max_storable_order = max(0, sku_max_cap - (current_stock + current_incoming))
            checks.append({
                "rule_name": "Storage Capacity Limit",
                "category": "spatial",
                "passed": False,
                "severity": "error",
                "message": f"Inventory pipeline ({net_after_delivery} units) exceeds maximum SKU shelf capacity ({sku_max_cap} units) by {overflow} units.",
                "details": {
                    "current_stock": current_stock,
                    "existing_pipeline": current_incoming,
                    "new_order_qty": total_new_qty,
                    "sku_max_capacity": sku_max_cap,
                    "max_storable_new_qty": max_storable_order
                }
            })
            feedback_notes.append(
                f"STORAGE CAPACITY VIOLATION: Maximum new units that can be stored is {max_storable_order} units (shelf limit {sku_max_cap})."
            )
        else:
            free_slots_remaining = sku_max_cap - net_after_delivery
            checks.append({
                "rule_name": "Storage Capacity Limit",
                "category": "spatial",
                "passed": True,
                "severity": "info",
                "message": f"Passed: Post-receipt inventory ({net_after_delivery} units) fits comfortably within {sku_max_cap} capacity ({free_slots_remaining} buffer slots remaining).",
                "details": {"free_slots_remaining": free_slots_remaining}
            })

        # -------------------------------------------------------------
        # CHECK 3: Supplier Constraints (MOQ, Max Qty, Availability)
        # -------------------------------------------------------------
        for act in actions:
            act_sup_id = act.get("supplier_id") or supplier_id
            act_qty = int(act.get("qty", 0))
            if not act_sup_id or act_qty <= 0:
                continue

            sup_res = await self.session.execute(select(Supplier).where(Supplier.id == act_sup_id))
            sup = sup_res.scalar_one_or_none()

            sp_res = await self.session.execute(
                select(SupplierProduct).where(
                    SupplierProduct.product_id == product_id,
                    SupplierProduct.supplier_id == act_sup_id
                )
            )
            sp = sp_res.scalar_one_or_none()

            if sup:
                if act_qty < sup.min_order_qty:
                    is_passed = False
                    checks.append({
                        "rule_name": f"Supplier MOQ Check ({sup.name})",
                        "category": "supplier_constraint",
                        "passed": False,
                        "severity": "error",
                        "message": f"Order quantity ({act_qty}) is below supplier minimum order quantity ({sup.min_order_qty} units).",
                        "details": {"requested": act_qty, "moq": sup.min_order_qty}
                    })
                    feedback_notes.append(
                        f"MOQ VIOLATION: Supplier {sup.name} requires minimum {sup.min_order_qty} units."
                    )
                else:
                    checks.append({
                        "rule_name": f"Supplier MOQ Check ({sup.name})",
                        "category": "supplier_constraint",
                        "passed": True,
                        "severity": "info",
                        "message": f"Passed: Quantity {act_qty} satisfies MOQ of {sup.min_order_qty}."
                    })

                if sp and act_qty > sp.available_qty:
                    is_passed = False
                    checks.append({
                        "rule_name": f"Supplier Inventory Stock Check ({sup.name})",
                        "category": "supplier_constraint",
                        "passed": False,
                        "severity": "error",
                        "message": f"Requested {act_qty} units, but supplier has only {sp.available_qty} units in stock.",
                        "details": {"requested": act_qty, "supplier_available": sp.available_qty}
                    })
                    feedback_notes.append(
                        f"SUPPLIER STOCK SHORTFALL: {sup.name} can only supply {sp.available_qty} units. Remaining units must be split or sourced from an alternative supplier."
                    )
                elif sp:
                    checks.append({
                        "rule_name": f"Supplier Inventory Stock Check ({sup.name})",
                        "category": "supplier_constraint",
                        "passed": True,
                        "severity": "info",
                        "message": f"Passed: Supplier has {sp.available_qty} units available (order takes {act_qty})."
                    })

        # -------------------------------------------------------------
        # CHECK 4: Demand Coverage & Stockout Prevention
        # -------------------------------------------------------------
        if forecast:
            expected_demand = forecast.actual_run_rate_qty if forecast.trend == "spiking" else forecast.forecasted_qty
            safety_stock = inventory.safety_stock if inventory else 50
            total_projected_stock = current_stock + current_incoming + total_new_qty
            needed_stock = expected_demand + safety_stock

            # If the warehouse shelf capacity is already reached (>= 90% full), this is an optimal phased wave
            is_at_capacity = (total_projected_stock >= (sku_max_cap * 0.9))

            if total_projected_stock < (expected_demand * 0.7) and not is_at_capacity:
                is_passed = False
                deficit = needed_stock - total_projected_stock
                checks.append({
                    "rule_name": "Demand Coverage / Stockout Prevention",
                    "category": "demand_coverage",
                    "passed": False,
                    "severity": "error",
                    "message": f"Stockout Risk: Total available + ordered ({total_projected_stock} units) covers less than 70% of expected demand ({expected_demand} units). Deficit: {deficit} units.",
                    "details": {"projected": total_projected_stock, "target_need": needed_stock}
                })
                feedback_notes.append(
                    f"STOCKOUT HAZARD: Projected stock of {total_projected_stock} units leaves a deficit of {deficit} units against expected demand of {expected_demand}."
                )
            elif is_at_capacity and total_projected_stock < (expected_demand * 0.7):
                checks.append({
                    "rule_name": "Phased Wave Capacity Optimization",
                    "category": "demand_coverage",
                    "passed": True,
                    "severity": "info",
                    "message": f"Passed: Maximum allowable wave size ({total_projected_stock}/{sku_max_cap} shelf units) scheduled. Wave 2 to trigger post sell-through.",
                    "details": {"current_wave_stock": total_projected_stock, "max_capacity": sku_max_cap}
                })
            elif total_projected_stock > (needed_stock * 2.2) and decision_type != "reject":
                has_warnings = True
                excess = total_projected_stock - needed_stock
                checks.append({
                    "rule_name": "Working Capital & Overstock Risk",
                    "category": "demand_coverage",
                    "passed": True,
                    "severity": "warning",
                    "message": f"Overstock Warning: Total projected stock ({total_projected_stock} units) exceeds 220% of target need ({needed_stock} units) by {excess} units.",
                    "details": {"excess_units": excess}
                })
            else:
                coverage_days = round((total_projected_stock / (expected_demand / 30.0)), 1) if expected_demand > 0 else 30
                checks.append({
                    "rule_name": "Demand Coverage / Stockout Prevention",
                    "category": "demand_coverage",
                    "passed": True,
                    "severity": "info",
                    "message": f"Passed: Total coverage ({total_projected_stock} units) provides ~{coverage_days} days of forward sales coverage.",
                    "details": {"coverage_days": coverage_days}
                })

        # -------------------------------------------------------------
        # CHECK 5: Supplier Reliability & Risk Exposure
        # -------------------------------------------------------------
        for act in actions:
            act_sup_id = act.get("supplier_id") or supplier_id
            if act_sup_id:
                sup_res = await self.session.execute(select(Supplier).where(Supplier.id == act_sup_id))
                sup = sup_res.scalar_one_or_none()
                if sup and sup.reliability_score < 0.85:
                    has_warnings = True
                    checks.append({
                        "rule_name": f"Supplier Reliability Advisory ({sup.name})",
                        "category": "reliability",
                        "passed": True,
                        "severity": "warning",
                        "message": f"Supplier historical fulfillment rate is {int(sup.reliability_score * 100)}% (< 85% benchmark). Consider buffer lead time or secondary vendor backup.",
                        "details": {"reliability_score": sup.reliability_score}
                    })

        status = "passed" if is_passed and not has_warnings else ("warning" if is_passed else "failed")

        return {
            "passed": is_passed,
            "status": status,
            "checks": checks,
            "total_checks": len(checks),
            "passed_checks_count": sum(1 for c in checks if c["passed"]),
            "failed_checks_count": sum(1 for c in checks if not c["passed"]),
            "warnings_count": sum(1 for c in checks if c["severity"] == "warning"),
            "feedback_for_agent": "\n".join(feedback_notes) if feedback_notes else "All operational, budget, and capacity constraints satisfied."
        }
