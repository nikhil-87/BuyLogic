import pytest
import asyncio
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models import Scenario, Product, Inventory, SupplierProduct
from backend.agent.tools import AgentToolsExecutor
from backend.agent.validator import DecisionValidator
from backend.seed import seed_data

@pytest.mark.asyncio
async def test_seed_and_models():
    await seed_data()
    async with AsyncSessionLocal() as session:
        scenarios = (await session.execute(select(Scenario))).scalars().all()
        assert len(scenarios) == 4
        products = (await session.execute(select(Product))).scalars().all()
        assert len(products) == 4

@pytest.mark.asyncio
async def test_agent_tools():
    await seed_data()
    async with AsyncSessionLocal() as session:
        executor = AgentToolsExecutor(session)

        # Test check_inventory
        inv = await executor.execute_tool("check_inventory", {"product_id": "PROD-EARBUDS-01", "node_id": "NODE-NORTH-01"})
        assert inv["current_stock"] == 320
        assert inv["safety_stock"] == 100
        assert inv["max_capacity"] == 1000

        # Test check_open_purchase_orders
        pos = await executor.execute_tool("check_open_purchase_orders", {"product_id": "PROD-EARBUDS-01"})
        assert pos["open_po_count"] >= 1
        assert pos["total_incoming_quantity"] >= 200

        # Test check_demand_forecast
        fc = await executor.execute_tool("check_demand_forecast", {"product_id": "PROD-POWER-03"})
        assert fc["anomaly_detected"] is True
        assert fc["actual_30d_run_rate"] == 950

        # Test check_suppliers
        sups = await executor.execute_tool("check_suppliers", {"product_id": "PROD-COFFEE-02"})
        assert sups["available_suppliers_count"] >= 2

@pytest.mark.asyncio
async def test_decision_validator_catches_violations():
    await seed_data()
    async with AsyncSessionLocal() as session:
        validator = DecisionValidator(session)

        # 1. Test violation: 800 units of Earbuds exceeds storage (current 320 + incoming 200 + 800 = 1320 > 1000 max capacity)
        # and exceeds budget ($36,000 > $35,000 remaining)
        res_violation = await validator.validate_decision(
            scenario_id="scenario_1",
            product_id="PROD-EARBUDS-01",
            node_id="NODE-NORTH-01",
            decision_type="create_po",
            recommended_qty=800,
            supplier_id="SUP-01"
        )
        assert res_violation["passed"] is False
        assert res_violation["failed_checks_count"] >= 1

        # 2. Test compliance: 380 units fits storage (320 + 200 + 380 = 900 <= 1000) and budget ($17,100 <= $35,000)
        res_valid = await validator.validate_decision(
            scenario_id="scenario_1",
            product_id="PROD-EARBUDS-01",
            node_id="NODE-NORTH-01",
            decision_type="modify",
            recommended_qty=380,
            supplier_id="SUP-01"
        )
        assert res_valid["passed"] is True
