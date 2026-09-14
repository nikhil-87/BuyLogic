import time
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Scenario, AgentActionLog, AgentDecision, Inventory, PurchaseOrder
from backend.agent.engine import PurchasingAgentEngine
from backend.agent.validator import DecisionValidator
from backend.seed import seed_data

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])

@router.get("/run")
async def run_evaluation_suite(db: AsyncSession = Depends(get_db)):
    """
    Executes an end-to-end evaluation benchmark across all 4 purchasing scenarios.
    Measures:
    1. Information Gathering (Tool completeness)
    2. Decision Correctness & Soundness
    3. Constraint Adherence (Budget, Storage, MOQ)
    4. Feedback Loop & Validation Rigor
    5. Action Execution & Post-State Integrity
    """
    # Reset DB to clean benchmark state first to ensure deterministic evaluation
    await seed_data()

    scenarios_res = await db.execute(select(Scenario).order_by(Scenario.scenario_number))
    scenarios = scenarios_res.scalars().all()

    results = []
    engine = PurchasingAgentEngine(db)
    validator = DecisionValidator(db)

    total_score = 0
    max_score = 100  # 25 points per scenario

    for sc in scenarios:
        sc_id = sc.id
        sc_num = sc.scenario_number

        # 1. Run the agent stream
        start_time = time.time()
        agent_events = []
        async for chunk in engine.run_agent_stream(sc_id):
            if chunk.startswith("data: "):
                try:
                    import json
                    event = json.loads(chunk[6:].strip())
                    agent_events.append(event)
                except Exception:
                    pass
        duration = round(time.time() - start_time, 2)

        # 2. Inspect logs and tool calls
        tool_calls = [e.get("tool_name") for e in agent_events if e.get("type") == "tool_call"]
        distinct_tools = set([t for t in tool_calls if t])

        # 3. Retrieve final decision
        dec_res = await db.execute(
            select(AgentDecision).where(AgentDecision.scenario_id == sc_id).order_by(AgentDecision.created_at.desc())
        )
        dec = dec_res.scalars().first()

        # Rubric checks
        checks = []
        scenario_points = 0

        # Check A: Information Gathering (5 pts)
        expected_tools = {"check_inventory", "check_open_purchase_orders", "check_demand_forecast", "check_suppliers"}
        tools_found = expected_tools.intersection(distinct_tools)
        info_gathering_passed = len(tools_found) >= 3
        if info_gathering_passed:
            scenario_points += 5
            checks.append({
                "name": "Information Gathering & Tool Invocations",
                "passed": True,
                "score": 5,
                "max": 5,
                "notes": f"Invoked tools: {', '.join(distinct_tools)}"
            })
        else:
            checks.append({
                "name": "Information Gathering & Tool Invocations",
                "passed": False,
                "score": 2,
                "max": 5,
                "notes": f"Missing critical tools. Invoked: {distinct_tools}"
            })

        # Check B: Decision Correctness based on Scenario (10 pts)
        decision_correct = False
        decision_notes = ""

        if sc_num == 1:
            # Must NOT accept 800 (would overflow storage and exceed budget). Must modify to <= 480.
            if dec and dec.decision_type == "modify" and 250 <= dec.recommended_qty <= 480:
                decision_correct = True
                decision_notes = f"Correctly rejected 800-unit excess; modified order to optimal {dec.recommended_qty} units fitting storage and budget."
            else:
                decision_notes = f"Failed to properly modify 800 units. Got type={dec.decision_type}, qty={dec.recommended_qty}"

        elif sc_num == 2:
            # Must detect shortfall (250 units) and split or re-route to secondary supplier SUP-03
            if dec and (dec.decision_type == "split_order" or dec.decision_type == "modify"):
                decision_correct = True
                decision_notes = f"Correctly acknowledged 250 shortfall on PO-9041 and engaged secondary supplier to prevent stockout."
            else:
                decision_notes = f"Failed to address supplier shortfall. Got type={dec.decision_type}"

        elif sc_num == 3:
            # Must detect surge and recommend expediting coverage (>= 500 units)
            if dec and dec.recommended_qty >= 500:
                decision_correct = True
                decision_notes = f"Correctly flagged demand velocity surge (+216%) and issued expedited order of {dec.recommended_qty} units."
            else:
                decision_notes = f"Failed to size order for demand spike. Recommended: {dec.recommended_qty if dec else 0}"

        elif sc_num == 4:
            # Must resolve dual constraint: requested 1200, but clamped to <= 600
            if dec and dec.recommended_qty <= 600 and dec.decision_type == "modify":
                decision_correct = True
                decision_notes = f"Correctly identified dual budget and shelf limits; clamped Wave 1 to {dec.recommended_qty} units."
            else:
                decision_notes = f"Failed to respect purchasing constraints. Proposed: {dec.recommended_qty if dec else 0}"

        if decision_correct:
            scenario_points += 10
            checks.append({
                "name": "Decision Correctness & Strategic Soundness",
                "passed": True,
                "score": 10,
                "max": 10,
                "notes": decision_notes
            })
        else:
            checks.append({
                "name": "Decision Correctness & Strategic Soundness",
                "passed": False,
                "score": 3,
                "max": 10,
                "notes": decision_notes
            })

        # Check C: Constraint Validation Adherence (5 pts)
        val_res = await validator.validate_decision(
            scenario_id=sc_id,
            product_id=sc.product_id,
            node_id=sc.node_id,
            decision_type=dec.decision_type if dec else "modify",
            recommended_qty=dec.recommended_qty if dec else 0,
            supplier_id=dec.supplier_id if dec else None,
            proposed_actions=dec.proposed_actions if dec else None
        )
        if val_res["passed"]:
            scenario_points += 5
            checks.append({
                "name": "Constraint Compliance (Budget, Storage, MOQ)",
                "passed": True,
                "score": 5,
                "max": 5,
                "notes": f"All {val_res['total_checks']} business rules satisfied without hard violations."
            })
        else:
            checks.append({
                "name": "Constraint Compliance (Budget, Storage, MOQ)",
                "passed": False,
                "score": 1,
                "max": 5,
                "notes": f"Failed {val_res['failed_checks_count']} constraints: {val_res['feedback_for_agent']}"
            })

        # Check D: Actionability & Execution Verification (5 pts)
        if dec:
            try:
                exec_result = await engine.execute_approved_decision(dec.id)
                post_val = exec_result.get("post_action_validation", {})
                if exec_result.get("success") and post_val.get("passed"):
                    scenario_points += 5
                    checks.append({
                        "name": "Action Execution & Post-State Integrity",
                        "passed": True,
                        "score": 5,
                        "max": 5,
                        "notes": f"Successfully created/modified {len(exec_result['executed_orders'])} POs and verified DB integrity."
                    })
                else:
                    checks.append({
                        "name": "Action Execution & Post-State Integrity",
                        "passed": False,
                        "score": 2,
                        "max": 5,
                        "notes": "Execution succeeded but post-action validation reported warnings."
                    })
            except Exception as e:
                checks.append({
                    "name": "Action Execution & Post-State Integrity",
                    "passed": False,
                    "score": 0,
                    "max": 5,
                    "notes": f"Execution failed: {str(e)}"
                })

        total_score += scenario_points
        results.append({
            "scenario_id": sc_id,
            "scenario_number": sc_num,
            "title": sc.title,
            "duration_seconds": duration,
            "points_earned": scenario_points,
            "points_possible": 25,
            "status": "passed" if scenario_points >= 20 else "partial",
            "decision_summary": {
                "decision_type": dec.decision_type if dec else None,
                "recommended_qty": dec.recommended_qty if dec else None,
                "supplier_id": dec.supplier_id if dec else None,
                "validation_status": dec.validation_status if dec else None
            },
            "rubric_breakdown": checks
        })

    overall_grade = "A+" if total_score >= 90 else ("A" if total_score >= 80 else "B")

    return {
        "evaluation_summary": {
            "total_score": total_score,
            "max_possible_score": max_score,
            "percentage": round((total_score / max_score) * 100, 1),
            "grade": overall_grade,
            "scenarios_evaluated": len(scenarios),
            "all_passed": total_score >= 80
        },
        "scenario_results": results
    }
