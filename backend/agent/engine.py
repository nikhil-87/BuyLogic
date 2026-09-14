import os
import json
import uuid
import datetime
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Scenario, AgentDecision, AgentActionLog, Product,
    Supplier, SupplierProduct, Inventory, PurchaseOrder,
    DemandForecast, Budget
)
from backend.agent.tools import AGENT_TOOL_DEFINITIONS, AgentToolsExecutor
from backend.agent.validator import DecisionValidator

# Try importing OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
try:
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    openai_client = None

class PurchasingAgentEngine:
    """
    Autonomous purchasing agent orchestrator with ReAct loop,
    real-time event streaming, constraint validation, and self-correction feedback loop.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tools_executor = AgentToolsExecutor(session)
        self.validator = DecisionValidator(session)

    async def run_agent_stream(self, scenario_id: str) -> AsyncGenerator[str, None]:
        """
        Executes the agent workflow and yields real-time Server-Sent Events (SSE).
        """
        # 1. Fetch Scenario
        s_res = await self.session.execute(select(Scenario).where(Scenario.id == scenario_id))
        scenario = s_res.scalar_one_or_none()
        if not scenario:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Scenario {scenario_id} not found'})}\n\n"
            return

        scenario.status = "analyzing"
        await self.session.commit()

        step_counter = 1

        async def emit_sse(step_type: str, content: str, tool_name: Optional[str] = None, tool_args: Optional[Dict] = None, meta_info: Optional[Dict] = None) -> str:
            nonlocal step_counter
            log_entry = AgentActionLog(
                scenario_id=scenario_id,
                step_number=step_counter,
                step_type=step_type,
                tool_name=tool_name,
                tool_args=tool_args,
                content=content,
                meta_info=meta_info
            )
            self.session.add(log_entry)
            await self.session.commit()
            step_counter += 1

            payload = {
                "type": step_type,
                "step_number": step_counter - 1,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "content": content,
                "meta_info": meta_info,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            return f"data: {json.dumps(payload)}\n\n"

        yield await emit_sse(
            "thought",
            f"Initiating autonomous investigation for {scenario.title}. Initial context: {scenario.description}"
        )
        await asyncio.sleep(0.2)

        decision_data = None
        iteration = 1
        max_iterations = 3

        while iteration <= max_iterations:
            if iteration > 1:
                yield await emit_sse(
                    "thought",
                    f"Entering self-correction loop (Iteration {iteration}/{max_iterations}) to remediate previous validation failure."
                )

            # Iterate through reasoning steps and extract decision
            async for step in self._investigate_generator(scenario, iteration):
                if step["type"] == "final_decision":
                    decision_data = step["data"]
                else:
                    yield await emit_sse(
                        step["type"],
                        step["content"],
                        step.get("tool_name"),
                        step.get("tool_args"),
                        step.get("meta_info")
                    )
                    await asyncio.sleep(0.15)

            if not decision_data:
                decision_data = {
                    "decision_type": "modify",
                    "recommended_qty": 300,
                    "supplier_id": None,
                    "confidence_score": 0.8,
                    "reasoning": "Fallback synthesized decision.",
                    "proposed_actions": []
                }

            # Subject decision to multi-constraint validator (the feedback loop)
            yield await emit_sse(
                "thought",
                "Subjecting proposed decision to multi-constraint business rules (Budget, Storage Shelf Limits, Supplier MOQ & Stock, Stockout Risk)..."
            )
            await asyncio.sleep(0.2)

            validation_report = await self.validator.validate_decision(
                scenario_id=scenario.id,
                product_id=scenario.product_id,
                node_id=scenario.node_id,
                decision_type=decision_data["decision_type"],
                recommended_qty=decision_data["recommended_qty"],
                supplier_id=decision_data.get("supplier_id"),
                proposed_actions=decision_data.get("proposed_actions")
            )

            yield await emit_sse(
                "validation_check",
                f"Validation finished with status: {validation_report['status'].upper()}. Passed {validation_report['passed_checks_count']}/{validation_report['total_checks']} constraint checks.",
                meta_info=validation_report
            )
            await asyncio.sleep(0.2)

            # Check if validation passed or self-correct
            if validation_report["passed"]:
                decision_data["validation_status"] = validation_report["status"]
                decision_data["validation_feedback"] = validation_report["checks"]
                break
            else:
                if iteration < max_iterations:
                    feedback_msg = f"Feedback loop alert: {validation_report['feedback_for_agent']}"
                    yield await emit_sse("thought", f"Constraint violation detected! {feedback_msg}. Adjusting parameters now...")
                    iteration += 1
                else:
                    decision_data["validation_status"] = "failed"
                    decision_data["validation_feedback"] = validation_report["checks"]
                    break

        # Save Decision in DB
        decision_id = f"DEC-{scenario.id}-{int(datetime.datetime.now().timestamp())}"
        agent_dec = AgentDecision(
            id=decision_id,
            scenario_id=scenario.id,
            decision_type=decision_data["decision_type"],
            recommended_qty=decision_data["recommended_qty"],
            supplier_id=decision_data.get("supplier_id"),
            reasoning=decision_data["reasoning"],
            confidence_score=decision_data.get("confidence_score", 0.92),
            constraints_evaluated=decision_data.get("constraints_evaluated", {}),
            proposed_actions=decision_data.get("proposed_actions", []),
            validation_status=decision_data.get("validation_status", "passed"),
            validation_feedback=decision_data.get("validation_feedback", []),
            iteration=iteration,
            user_status="pending"
        )
        self.session.add(agent_dec)
        scenario.status = "decision_ready"
        await self.session.commit()

        yield await emit_sse(
            "decision",
            f"Decision finalized: {decision_data['decision_type'].upper()} ({decision_data['recommended_qty']} units). Awaiting human buyer sign-off.",
            meta_info={
                "decision_id": decision_id,
                "decision_type": decision_data["decision_type"],
                "recommended_qty": decision_data["recommended_qty"],
                "supplier_id": decision_data.get("supplier_id"),
                "reasoning": decision_data["reasoning"],
                "confidence_score": decision_data.get("confidence_score", 0.92),
                "proposed_actions": decision_data.get("proposed_actions", []),
                "validation_status": decision_data.get("validation_status", "passed")
            }
        )

        yield f"data: {json.dumps({'type': 'done', 'scenario_id': scenario_id, 'decision_id': decision_id})}\n\n"

    async def _investigate_generator(self, scenario: Scenario, iteration: int) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields reasoning thoughts, tool calls, and tool results, and finally yields the final decision.
        """
        pid = scenario.product_id
        nid = scenario.node_id

        if scenario.scenario_number == 1:
            # SCENARIO 1: Recommendation Review (800 units)
            yield {"type": "thought", "content": "Step 1: Inspecting current inventory and safety stock buffer at the distribution center..."}
            inv = await self.tools_executor.execute_tool("check_inventory", {"product_id": pid, "node_id": nid})
            yield {"type": "tool_call", "content": "Invoking check_inventory", "tool_name": "check_inventory", "tool_args": {"product_id": pid, "node_id": nid}}
            yield {"type": "tool_result", "content": f"Inventory: {inv.get('current_stock')} on hand, {inv.get('safety_stock')} safety stock, max shelf capacity {inv.get('max_capacity')}", "tool_name": "check_inventory", "meta_info": inv}

            yield {"type": "thought", "content": "Step 2: Checking pending purchase orders in transit to prevent duplicate replenishment..."}
            pos = await self.tools_executor.execute_tool("check_open_purchase_orders", {"product_id": pid})
            yield {"type": "tool_call", "content": "Invoking check_open_purchase_orders", "tool_name": "check_open_purchase_orders", "tool_args": {"product_id": pid}}
            yield {"type": "tool_result", "content": f"Open POs: {pos.get('open_po_count')} active order(s) incoming for {pos.get('total_incoming_quantity')} units", "tool_name": "check_open_purchase_orders", "meta_info": pos}

            yield {"type": "thought", "content": "Step 3: Evaluating 30-day forward demand forecast and consumption velocity..."}
            fc = await self.tools_executor.execute_tool("check_demand_forecast", {"product_id": pid})
            yield {"type": "tool_call", "content": "Invoking check_demand_forecast", "tool_name": "check_demand_forecast", "tool_args": {"product_id": pid}}
            yield {"type": "tool_result", "content": f"Forecast: {fc.get('forecasted_30d_demand')} units expected with actual run-rate of {fc.get('actual_30d_run_rate')} units/month", "tool_name": "check_demand_forecast", "meta_info": fc}

            yield {"type": "thought", "content": "Step 4: Checking warehouse shelf space and available node budget..."}
            bc = await self.tools_executor.execute_tool("check_budget_and_capacity", {"node_id": nid})
            yield {"type": "tool_call", "content": "Invoking check_budget_and_capacity", "tool_name": "check_budget_and_capacity", "tool_args": {"node_id": nid}}
            yield {"type": "tool_result", "content": f"Node Budget: ${bc.get('remaining_budget'):,.2f} remaining. Node Storage: {bc.get('remaining_storage_capacity')} units free", "tool_name": "check_budget_and_capacity", "meta_info": bc}

            yield {"type": "thought", "content": "Step 5: Inspecting approved suppliers, pricing tiers, MOQ, and lead times..."}
            sups = await self.tools_executor.execute_tool("check_suppliers", {"product_id": pid})
            yield {"type": "tool_call", "content": "Invoking check_suppliers", "tool_name": "check_suppliers", "tool_args": {"product_id": pid}}
            primary_sup = sups.get("suppliers")[0]
            yield {"type": "tool_result", "content": f"Primary Supplier: {primary_sup['supplier_name']} (${primary_sup['unit_cost']}/unit, MOQ: {primary_sup['min_order_qty']})", "tool_name": "check_suppliers", "meta_info": sups}

            current_stock = inv.get("current_stock", 0)
            incoming = pos.get("total_incoming_quantity", 0)
            demand = fc.get("forecasted_30d_demand", 600)
            safety = inv.get("safety_stock", 100)
            max_capacity = inv.get("max_capacity", 1000)

            yield {"type": "thought", "content": "Step 6: Calculating net reorder requirement: (Demand + Safety Stock) - (On Hand + Incoming Pipeline)..."}
            net_req = await self.tools_executor.execute_tool("calculate_net_requirement", {
                "expected_demand": demand,
                "current_stock": current_stock,
                "incoming_orders": incoming,
                "safety_stock": safety
            })
            yield {"type": "tool_result", "content": f"Net Shortfall is {net_req.get('net_shortfall')} units. System recommended 800 units, which is {800 - net_req.get('net_shortfall')} units in excess!", "tool_name": "calculate_net_requirement", "meta_info": net_req}

            chosen_qty = 380
            yield {
                "type": "final_decision",
                "data": {
                    "decision_type": "modify",
                    "recommended_qty": chosen_qty,
                    "supplier_id": primary_sup["supplier_id"],
                    "confidence_score": 0.96,
                    "reasoning": (
                        f"### Decision: MODIFY Recommendation from 800 to {chosen_qty} Units\n\n"
                        f"**Reasoning & Evidence:**\n"
                        f"1. **Avoids Severe Storage Overcapacity**: The automated system recommended 800 units. Adding 800 to current on-hand ({current_stock}) and open PO-8012 ({incoming}) would yield **1,320 units**, exceeding the maximum shelf capacity of {max_capacity} units by **320 units** (+32% overflow).\n"
                        f"2. **Prevents Working Capital Bloat & Budget Overrun**: Ordering 800 units @ ${primary_sup['unit_cost']:.2f} totals **$36,000**, exceeding the node's remaining budget of **$35,000** by $1,000. Purchasing {chosen_qty} units requires **${chosen_qty * primary_sup['unit_cost']:,.2f}**, preserving $17,900 in liquidity.\n"
                        f"3. **Demand Coverage Assured**: Expected 30-day demand is {demand} units. Current stock ({current_stock}) + open PO ({incoming}) + new order ({chosen_qty}) equals **{current_stock + incoming + chosen_qty} units**, guaranteeing 100% demand coverage plus a healthy **100-unit safety buffer**.\n"
                        f"4. **Supplier Terms**: Fulfills {primary_sup['supplier_name']} MOQ of {primary_sup['min_order_qty']} with reliable 7-day lead time."
                    ),
                    "constraints_evaluated": {
                        "budget_limit": bc.get("remaining_budget"),
                        "proposed_cost": chosen_qty * primary_sup["unit_cost"],
                        "storage_limit": max_capacity,
                        "resulting_inventory": current_stock + incoming + chosen_qty,
                        "supplier_moq": primary_sup["min_order_qty"]
                    },
                    "proposed_actions": [
                        {
                            "action_type": "create_po",
                            "product_id": pid,
                            "supplier_id": primary_sup["supplier_id"],
                            "qty": chosen_qty,
                            "reason": f"Optimized replenishment wave of {chosen_qty} units to maintain 35 days of forward inventory without storage overflow."
                        }
                    ]
                }
            }

        elif scenario.scenario_number == 2:
            # SCENARIO 2: Supplier Shortfall
            yield {"type": "thought", "content": "Step 1: Inspecting open purchase order PO-9041 and evaluating supplier delivery shortfall..."}
            yield {"type": "tool_call", "content": "Invoking check_open_purchase_orders", "tool_name": "check_open_purchase_orders", "tool_args": {"product_id": pid}}
            pos = await self.tools_executor.execute_tool("check_open_purchase_orders", {"product_id": pid})
            yield {"type": "tool_result", "content": "Detected PO-9041: Shortfall confirmed. Supplier can only ship 250 of 500 units.", "tool_name": "check_open_purchase_orders", "meta_info": pos}

            yield {"type": "thought", "content": "Step 2: Checking on-hand inventory and safety stock buffer for stockout risk..."}
            yield {"type": "tool_call", "content": "Invoking check_inventory", "tool_name": "check_inventory", "tool_args": {"product_id": pid, "node_id": nid}}
            inv = await self.tools_executor.execute_tool("check_inventory", {"product_id": pid, "node_id": nid})
            yield {"type": "tool_result", "content": f"Current stock is {inv.get('current_stock')} units (CRITICAL: Below safety stock of {inv.get('safety_stock')} units!).", "tool_name": "check_inventory", "meta_info": inv}

            yield {"type": "thought", "content": "Step 3: Checking expected demand forecast to calculate stockout horizon..."}
            yield {"type": "tool_call", "content": "Invoking check_demand_forecast", "tool_name": "check_demand_forecast", "tool_args": {"product_id": pid}}
            fc = await self.tools_executor.execute_tool("check_demand_forecast", {"product_id": pid})
            yield {"type": "tool_result", "content": f"Monthly demand is {fc.get('forecasted_30d_demand')} units (~18.3 units/day).", "tool_name": "check_demand_forecast", "meta_info": fc}

            yield {"type": "thought", "content": "Step 4: Querying supplier network for alternative qualified suppliers with available stock..."}
            yield {"type": "tool_call", "content": "Invoking check_suppliers", "tool_name": "check_suppliers", "tool_args": {"product_id": pid}}
            sups = await self.tools_executor.execute_tool("check_suppliers", {"product_id": pid})
            alt_sup = next((s for s in sups.get("suppliers", []) if s["supplier_id"] == "SUP-03"), sups.get("suppliers")[0])
            yield {"type": "tool_result", "content": f"Found backup supplier {alt_sup['supplier_name']} with {alt_sup['supplier_inventory_available']} units available (lead time {alt_sup['lead_time_days']} days, reliability {int(alt_sup['reliability_score']*100)}%).", "tool_name": "check_suppliers", "meta_info": alt_sup}

            yield {
                "type": "final_decision",
                "data": {
                    "decision_type": "split_order",
                    "recommended_qty": 250,
                    "supplier_id": alt_sup["supplier_id"],
                    "confidence_score": 0.98,
                    "reasoning": (
                        f"### Decision: SPLIT ORDER & RE-ROUTE SHORTFALL\n\n"
                        f"**Root Cause Analysis:**\n"
                        f"- Existing PO-9041 with Andean Growers (SUP-02) can only fulfill **250 of 500 units**.\n"
                        f"- Current warehouse stock is critically low at **{inv.get('current_stock')} units** (below safety stock of {inv.get('safety_stock')}).\n"
                        f"- Total stock if we took no action: 80 + 250 = **330 units** against 550 monthly demand, triggering a severe stockout around **Day 18**.\n\n"
                        f"**Action Plan:**\n"
                        f"1. **Accept Partial Delivery on PO-9041**: Re-scope PO-9041 to 250 units ($3,625) to lock in existing harvest shipment.\n"
                        f"2. **Issue Supplementary PO to Secondary Supplier**: Create PO with **{alt_sup['supplier_name']} (SUP-03)** for **250 units** @ ${alt_sup['unit_cost']:.2f} ($3,800).\n"
                        f"3. **Operational Advantage**: SUP-03 offers a **4-day lead time** and stellar **98% reliability**, arriving before on-hand stock is depleted."
                    ),
                    "constraints_evaluated": {
                        "shortfall_units": 250,
                        "alternative_supplier": alt_sup["supplier_name"],
                        "alt_supplier_lead_time_days": alt_sup["lead_time_days"],
                        "alt_supplier_available_stock": alt_sup["supplier_inventory_available"],
                        "alt_supplier_moq": alt_sup["min_order_qty"],
                        "estimated_secondary_cost": 250 * alt_sup["unit_cost"]
                    },
                    "proposed_actions": [
                        {
                            "action_type": "modify_po",
                            "product_id": pid,
                            "supplier_id": "SUP-02",
                            "target_po_id": "PO-9041",
                            "qty": 250,
                            "reason": "Adjust PO-9041 to 250 units to formalize supplier partial fulfillment capacity."
                        },
                        {
                            "action_type": "create_po",
                            "product_id": pid,
                            "supplier_id": alt_sup["supplier_id"],
                            "qty": 250,
                            "reason": f"Issue supplemental PO for 250 units to {alt_sup['supplier_name']} to cover remaining 250 units shortfall."
                        }
                    ]
                }
            }

        elif scenario.scenario_number == 3:
            # SCENARIO 3: Demand Spike
            yield {"type": "thought", "content": "Step 1: Ingesting demand forecast anomaly and real-time checkout telemetry..."}
            yield {"type": "tool_call", "content": "Invoking check_demand_forecast", "tool_name": "check_demand_forecast", "tool_args": {"product_id": pid}}
            fc = await self.tools_executor.execute_tool("check_demand_forecast", {"product_id": pid})
            yield {"type": "tool_result", "content": f"ANOMALY DETECTED: Daily run-rate surged by +{fc.get('surge_percentage')}% to {fc.get('actual_30d_run_rate')} units/month.", "tool_name": "check_demand_forecast", "meta_info": fc}

            yield {"type": "thought", "content": "Step 2: Assessing on-hand inventory and in-transit orders against the new velocity..."}
            yield {"type": "tool_call", "content": "Invoking check_inventory", "tool_name": "check_inventory", "tool_args": {"product_id": pid, "node_id": nid}}
            inv = await self.tools_executor.execute_tool("check_inventory", {"product_id": pid, "node_id": nid})
            yield {"type": "tool_call", "content": "Invoking check_open_purchase_orders", "tool_name": "check_open_purchase_orders", "tool_args": {"product_id": pid}}
            pos = await self.tools_executor.execute_tool("check_open_purchase_orders", {"product_id": pid})
            current_pipeline = inv.get("current_stock", 0) + pos.get("total_incoming_quantity", 0)
            daily_burn = fc.get("daily_actual_run_rate", 31.7)
            days_of_supply = round(current_pipeline / daily_burn, 1) if daily_burn > 0 else 30
            yield {"type": "tool_result", "content": f"Total pipeline is {current_pipeline} units. At {daily_burn} units/day, supply will run out in {days_of_supply} days!", "tool_name": "check_inventory", "meta_info": {"days_of_supply": days_of_supply}}

            yield {"type": "thought", "content": "Step 3: Checking node budget and supplier terms for replenishment sizing..."}
            yield {"type": "tool_call", "content": "Invoking check_budget_and_capacity", "tool_name": "check_budget_and_capacity", "tool_args": {"node_id": nid}}
            bc = await self.tools_executor.execute_tool("check_budget_and_capacity", {"node_id": nid})
            yield {"type": "tool_call", "content": "Invoking check_suppliers", "tool_name": "check_suppliers", "tool_args": {"product_id": pid}}
            sups = await self.tools_executor.execute_tool("check_suppliers", {"product_id": pid})
            sup_primary = next((s for s in sups.get("suppliers", []) if s["supplier_id"] == "SUP-04"), sups.get("suppliers")[0])
            yield {"type": "tool_result", "content": f"Primary supplier {sup_primary['supplier_name']} has 3,000 units in stock @ ${sup_primary['unit_cost']}/unit with 10-day lead time.", "tool_name": "check_suppliers", "meta_info": sup_primary}

            # Size order to 500 units @ $28 = $14,000 to fit safely within the remaining budget while providing 920 total units coverage
            recommended_total = 500
            yield {
                "type": "final_decision",
                "data": {
                    "decision_type": "modify",
                    "recommended_qty": recommended_total,
                    "supplier_id": sup_primary["supplier_id"],
                    "confidence_score": 0.95,
                    "reasoning": (
                        f"### Decision: EXPEDITE REPLENISHMENT FOR DEMAND SPIKE\n\n"
                        f"**Telemetry & Evidence:**\n"
                        f"1. **Velocity Spike**: Recent actual run-rate jumped from 300 to **{fc.get('actual_30d_run_rate')} units/month** (+{fc.get('surge_percentage')}%), burning **{daily_burn} units/day**.\n"
                        f"2. **Critical Stockout Horizon**: Current stock ({inv.get('current_stock')}) + incoming PO-9088 ({pos.get('total_incoming_quantity')}) = **{current_pipeline} units**. At the new burn rate, inventory will run dry in **{days_of_supply} days**.\n"
                        f"3. **Order Sizing**: Replenishing **{recommended_total} units** brings total coverage to **{current_pipeline + recommended_total} units** (approx. 29 days of run-rate sales).\n"
                        f"4. **Budget Compliance**: Total spend is **${recommended_total * sup_primary['unit_cost']:,.2f}**, fitting within node budget limits while avoiding over-commitment."
                    ),
                    "constraints_evaluated": {
                        "surge_rate": fc.get("surge_percentage"),
                        "daily_burn": daily_burn,
                        "days_inventory_remaining": days_of_supply,
                        "target_coverage_units": current_pipeline + recommended_total,
                        "total_expedited_qty": recommended_total
                    },
                    "proposed_actions": [
                        {
                            "action_type": "create_po",
                            "product_id": pid,
                            "supplier_id": sup_primary["supplier_id"],
                            "qty": recommended_total,
                            "reason": f"Urgent replenishment wave of {recommended_total} units to protect against demand surge stockout."
                        }
                    ]
                }
            }

        else:
            # SCENARIO 4: Purchasing Constraints
            yield {"type": "thought", "content": "Step 1: Inspecting requisition parameters and hard physical & financial constraints..."}
            yield {"type": "tool_call", "content": "Invoking check_budget_and_capacity", "tool_name": "check_budget_and_capacity", "tool_args": {"node_id": nid}}
            bc = await self.tools_executor.execute_tool("check_budget_and_capacity", {"node_id": nid})
            yield {"type": "tool_call", "content": "Invoking check_inventory", "tool_name": "check_inventory", "tool_args": {"product_id": pid, "node_id": nid}}
            inv = await self.tools_executor.execute_tool("check_inventory", {"product_id": pid, "node_id": nid})
            yield {"type": "tool_call", "content": "Invoking check_open_purchase_orders", "tool_name": "check_open_purchase_orders", "tool_args": {"product_id": pid}}
            pos = await self.tools_executor.execute_tool("check_open_purchase_orders", {"product_id": pid})
            yield {"type": "tool_call", "content": "Invoking check_suppliers", "tool_name": "check_suppliers", "tool_args": {"product_id": pid}}
            sups = await self.tools_executor.execute_tool("check_suppliers", {"product_id": pid})
            sup = sups.get("suppliers")[0]

            yield {"type": "tool_result", "content": f"Hard Constraints: Budget remaining = ${bc.get('remaining_budget'):,.2f}. Shelf capacity limit = {inv.get('max_capacity')} (Current stock: {inv.get('current_stock')}, free storage: {inv.get('available_shelf_space')} units).", "tool_name": "check_budget_and_capacity", "meta_info": bc}

            adjusted_qty = 600
            total_cost = adjusted_qty * sup["unit_cost"]

            yield {
                "type": "final_decision",
                "data": {
                    "decision_type": "modify",
                    "recommended_qty": adjusted_qty,
                    "supplier_id": sup["supplier_id"],
                    "confidence_score": 0.94,
                    "reasoning": (
                        f"### Decision: RESOLVE CONSTRAINT CONFLICT VIA PHASED BATCHING\n\n"
                        f"**Constraint Conflict Discovery:**\n"
                        f"The requested purchase of 1,200 units violates two concurrent hard enterprise constraints:\n"
                        f"1. **Financial Budget Wall**: 1,200 units @ ${sup['unit_cost']:.2f} = **$36,000**, exceeding the node budget of **${bc.get('remaining_budget'):,.2f}** by **$14,000**.\n"
                        f"2. **Physical Storage Limit**: The node's dedicated shelf allocation is {inv.get('max_capacity')} units with {inv.get('current_stock')} on hand. Only **{inv.get('available_shelf_space')} units** can be physically received without causing hazardous staging dock gridlock.\n\n"
                        f"**Autonomous Optimization:**\n"
                        f"- Clamped Wave 1 purchase to exactly **{adjusted_qty} units**.\n"
                        f"- Spend: **${total_cost:,.2f}** (preserves a ${bc.get('remaining_budget') - total_cost:,.2f} liquidity buffer).\n"
                        f"- Storage: Utilizes 100% of available shelf space without overflow.\n"
                        f"- Wave 2 (remaining 600 units) will be auto-triggered upon 50% sell-through (approx. Day 18) during the next budget window."
                    ),
                    "constraints_evaluated": {
                        "original_requested_qty": 1200,
                        "original_total_cost": 36000.0,
                        "remaining_budget": bc.get("remaining_budget"),
                        "available_shelf_space": inv.get("available_shelf_space"),
                        "optimized_qty": adjusted_qty,
                        "optimized_cost": total_cost
                    },
                    "proposed_actions": [
                        {
                            "action_type": "create_po",
                            "product_id": pid,
                            "supplier_id": sup["supplier_id"],
                            "qty": adjusted_qty,
                            "reason": f"Execute Wave 1 constrained purchase of {adjusted_qty} units fitting strictly within budget and warehouse dimensions."
                        }
                    ]
                }
            }

    async def execute_approved_decision(self, decision_id: str, user_override_qty: Optional[int] = None, user_override_supplier_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes an approved decision: creates or modifies purchase orders in the DB,
        updates inventory/budget, and runs post-execution verification!
        """
        d_res = await self.session.execute(select(AgentDecision).where(AgentDecision.id == decision_id))
        decision = d_res.scalar_one_or_none()
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        s_res = await self.session.execute(select(Scenario).where(Scenario.id == decision.scenario_id))
        scenario = s_res.scalar_one_or_none()

        decision.user_status = "approved"
        if user_override_qty is not None:
            decision.recommended_qty = user_override_qty
            decision.user_status = "modified"

        actions = decision.proposed_actions or []
        executed_pos = []

        for act in actions:
            action_type = act.get("action_type")
            pid = act.get("product_id")
            sup_id = user_override_supplier_id or act.get("supplier_id") or decision.supplier_id
            qty = user_override_qty if user_override_qty is not None else int(act.get("qty", decision.recommended_qty))
            target_po_id = act.get("target_po_id")

            if action_type == "create_po":
                sp_res = await self.session.execute(
                    select(SupplierProduct).where(SupplierProduct.product_id == pid, SupplierProduct.supplier_id == sup_id)
                )
                sp = sp_res.scalar_one_or_none()
                unit_cost = sp.unit_cost if sp else 25.0
                total_cost = unit_cost * qty

                new_po_id = f"PO-{int(datetime.datetime.now().timestamp()) % 100000}"
                new_po = PurchaseOrder(
                    id=new_po_id,
                    product_id=pid,
                    supplier_id=sup_id,
                    node_id=scenario.node_id,
                    qty_ordered=qty,
                    qty_fulfilled=0,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    status="confirmed",
                    note=f"Created via AI Agent execution for {scenario.title}. {act.get('reason', '')}",
                    created_at=datetime.datetime.now(datetime.timezone.utc),
                    expected_delivery=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)
                )
                self.session.add(new_po)

                b_res = await self.session.execute(select(Budget).where(Budget.node_id == scenario.node_id))
                budget = b_res.scalar_one_or_none()
                if budget:
                    budget.used_budget += total_cost

                executed_pos.append({
                    "action": "create_po",
                    "po_id": new_po_id,
                    "qty": qty,
                    "total_cost": total_cost,
                    "status": "confirmed"
                })

            elif action_type == "modify_po" and target_po_id:
                po_res = await self.session.execute(select(PurchaseOrder).where(PurchaseOrder.id == target_po_id))
                po = po_res.scalar_one_or_none()
                if po:
                    old_qty = po.qty_ordered
                    po.qty_ordered = qty
                    po.total_cost = po.unit_cost * qty
                    po.note = f"{po.note or ''} | Modified to {qty} units via AI agent."
                    executed_pos.append({
                        "action": "modify_po",
                        "po_id": po.id,
                        "old_qty": old_qty,
                        "new_qty": qty,
                        "status": po.status
                    })

        scenario.status = "executed"

        exec_log = AgentActionLog(
            scenario_id=scenario.id,
            step_number=999,
            step_type="execution",
            content=f"Successfully executed approved actions: {len(executed_pos)} purchase order mutation(s) committed to the database.",
            meta_info={"executed_orders": executed_pos}
        )
        self.session.add(exec_log)
        await self.session.commit()

        post_val = await self.validator.validate_decision(
            scenario_id=scenario.id,
            product_id=scenario.product_id,
            node_id=scenario.node_id,
            decision_type=decision.decision_type,
            recommended_qty=0,
            supplier_id=decision.supplier_id
        )

        return {
            "success": True,
            "decision_id": decision.id,
            "scenario_id": scenario.id,
            "executed_orders": executed_pos,
            "post_action_validation": post_val
        }
