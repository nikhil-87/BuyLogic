import asyncio
import datetime
from sqlalchemy import select
from backend.database import AsyncSessionLocal, engine, Base
from backend.models import (
    Product, Supplier, SupplierProduct, FulfillmentNode,
    Inventory, PurchaseOrder, DemandForecast, Budget,
    Scenario, AgentDecision, AgentActionLog
)

async def seed_data():
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Fulfillment Nodes
        nodes = [
            FulfillmentNode(
                id="NODE-NORTH-01",
                name="North Metro Hub (Bogota DC-1)",
                location="Calle 80 Logistics Corridor, Bogota",
                total_capacity=15000,
                used_capacity=10200
            ),
            FulfillmentNode(
                id="NODE-SOUTH-02",
                name="South Express Fulfillment (Medellin Hub)",
                location="Envigado Industrial Park, Medellin",
                total_capacity=12000,
                used_capacity=7400
            )
        ]
        session.add_all(nodes)
        await session.flush()

        # 2. Budgets
        budgets = [
            Budget(
                node_id="NODE-NORTH-01",
                department="Procurement",
                total_budget=60000.0,
                used_budget=25000.0,  # $35,000 remaining
                period="Current Month"
            ),
            Budget(
                node_id="NODE-SOUTH-02",
                department="Procurement",
                total_budget=45000.0,
                used_budget=23000.0,  # $22,000 remaining
                period="Current Month"
            )
        ]
        session.add_all(budgets)
        await session.flush()

        # 3. Products
        products = [
            Product(
                id="PROD-EARBUDS-01",
                sku="AWP-8800",
                name="AeroWireless Pro Earbuds",
                category="Consumer Electronics",
                unit_price=45.0,
                storage_units_per_item=1.0,
                description="Active noise-cancelling Bluetooth 5.3 earbuds with 36hr battery case."
            ),
            Product(
                id="PROD-COFFEE-02",
                sku="AOR-1020",
                name="Artisan Organic Roast Coffee 1kg",
                category="Gourmet Food & Beverage",
                unit_price=14.50,
                storage_units_per_item=1.5,
                description="Single-origin medium-dark roast whole beans from Huila highlands."
            ),
            Product(
                id="PROD-POWER-03",
                sku="UMP-3050",
                name="UltraFast Magnetic Power Bank 20000mAh",
                category="Mobile Accessories",
                unit_price=28.0,
                storage_units_per_item=1.0,
                description="Fast-charge 65W PD Qi2 magnetic power bank with digital display."
            ),
            Product(
                id="PROD-THERMOS-04",
                sku="EST-4010",
                name="Ergonomic Smart Thermos Bottle 750ml",
                category="Lifestyle & Drinkware",
                unit_price=30.0,
                storage_units_per_item=1.2,
                description="Vacuum-insulated stainless steel temperature touch display bottle."
            )
        ]
        session.add_all(products)
        await session.flush()

        # 4. Suppliers
        suppliers = [
            Supplier(
                id="SUP-01",
                name="Apex Sound Labs Global",
                lead_time_days=7,
                min_order_qty=100,
                max_order_qty=3000,
                reliability_score=0.96,
                active=True,
                contact_email="b2b@apexsound.com"
            ),
            Supplier(
                id="SUP-02",
                name="Andean Growers Collective",
                lead_time_days=5,
                min_order_qty=200,
                max_order_qty=1500,
                reliability_score=0.82,  # Experienced recent supply volatility
                active=True,
                contact_email="fulfillment@andeangrowers.co"
            ),
            Supplier(
                id="SUP-03",
                name="Sierra Mountain Roasters",
                lead_time_days=4,
                min_order_qty=150,
                max_order_qty=2000,
                reliability_score=0.98,
                active=True,
                contact_email="wholesale@sierracoop.org"
            ),
            Supplier(
                id="SUP-04",
                name="VoltTech Electronics Ltd",
                lead_time_days=10,
                min_order_qty=200,
                max_order_qty=4000,
                reliability_score=0.94,
                active=True,
                contact_email="supply@volttech.hk"
            ),
            Supplier(
                id="SUP-05",
                name="NovaEnergy Express Supply",
                lead_time_days=3,  # Expedited local partner
                min_order_qty=100,
                max_order_qty=1000,
                reliability_score=0.99,
                active=True,
                contact_email="priority@novaenergy.lat"
            ),
            Supplier(
                id="SUP-06",
                name="HydraTech Living Goods",
                lead_time_days=6,
                min_order_qty=300,
                max_order_qty=3500,
                reliability_score=0.95,
                active=True,
                contact_email="orders@hydratech.com"
            )
        ]
        session.add_all(suppliers)
        await session.flush()

        # 5. Supplier Products (Pricing, Stock, Preferred status)
        supplier_products = [
            SupplierProduct(
                supplier_id="SUP-01",
                product_id="PROD-EARBUDS-01",
                unit_cost=45.0,
                available_qty=2500,
                is_preferred=True
            ),
            SupplierProduct(
                supplier_id="SUP-02",
                product_id="PROD-COFFEE-02",
                unit_cost=14.50,
                available_qty=250,  # Shortfall: Only 250 available out of 500 contracted!
                is_preferred=True
            ),
            SupplierProduct(
                supplier_id="SUP-03",
                product_id="PROD-COFFEE-02",
                unit_cost=15.20,  # Slightly higher but available and highly reliable
                available_qty=1200,
                is_preferred=False
            ),
            SupplierProduct(
                supplier_id="SUP-04",
                product_id="PROD-POWER-03",
                unit_cost=28.0,
                available_qty=3000,
                is_preferred=True
            ),
            SupplierProduct(
                supplier_id="SUP-05",
                product_id="PROD-POWER-03",
                unit_cost=29.50,  # Emergency supplier
                available_qty=800,
                is_preferred=False
            ),
            SupplierProduct(
                supplier_id="SUP-06",
                product_id="PROD-THERMOS-04",
                unit_cost=30.0,
                available_qty=4000,
                is_preferred=True
            )
        ]
        session.add_all(supplier_products)
        await session.flush()

        # 6. Inventory Records
        inventories = [
            Inventory(
                product_id="PROD-EARBUDS-01",
                node_id="NODE-NORTH-01",
                current_stock=320,
                safety_stock=100,
                reserved_stock=35,
                max_capacity=1000  # Shelf capacity limit
            ),
            Inventory(
                product_id="PROD-COFFEE-02",
                node_id="NODE-NORTH-01",
                current_stock=80,  # Below safety stock!
                safety_stock=120,
                reserved_stock=15,
                max_capacity=1500
            ),
            Inventory(
                product_id="PROD-POWER-03",
                node_id="NODE-NORTH-01",
                current_stock=120,
                safety_stock=150,
                reserved_stock=20,
                max_capacity=1200
            ),
            Inventory(
                product_id="PROD-THERMOS-04",
                node_id="NODE-SOUTH-02",
                current_stock=150,
                safety_stock=80,
                reserved_stock=10,
                max_capacity=750  # Only ~600 free slots!
            )
        ]
        session.add_all(inventories)
        await session.flush()

        # 7. Existing Purchase Orders
        now = datetime.datetime.utcnow()
        pos = [
            PurchaseOrder(
                id="PO-8012",
                product_id="PROD-EARBUDS-01",
                supplier_id="SUP-01",
                node_id="NODE-NORTH-01",
                qty_ordered=200,
                qty_fulfilled=0,
                unit_cost=45.0,
                total_cost=9000.0,
                status="confirmed",
                note="Regular restocking wave. Expected in 3 days.",
                created_at=now - datetime.timedelta(days=4),
                expected_delivery=now + datetime.timedelta(days=3)
            ),
            PurchaseOrder(
                id="PO-9041",
                product_id="PROD-COFFEE-02",
                supplier_id="SUP-02",
                node_id="NODE-NORTH-01",
                qty_ordered=500,
                qty_fulfilled=0,
                unit_cost=14.50,
                total_cost=7250.0,
                status="partial",
                note="SUPPLIER ALERT: Supplier notified ability to ship only 250 units due to crop processing delay.",
                created_at=now - datetime.timedelta(days=2),
                expected_delivery=now + datetime.timedelta(days=3)
            ),
            PurchaseOrder(
                id="PO-9088",
                product_id="PROD-POWER-03",
                supplier_id="SUP-04",
                node_id="NODE-NORTH-01",
                qty_ordered=300,
                qty_fulfilled=0,
                unit_cost=28.0,
                total_cost=8400.0,
                status="confirmed",
                note="Standard monthly replenishment.",
                created_at=now - datetime.timedelta(days=5),
                expected_delivery=now + datetime.timedelta(days=5)
            )
        ]
        session.add_all(pos)
        await session.flush()

        # 8. Demand Forecasts
        forecasts = [
            DemandForecast(
                product_id="PROD-EARBUDS-01",
                node_id="NODE-NORTH-01",
                period="next_30_days",
                forecasted_qty=600,
                actual_run_rate_qty=580,
                trend="stable",
                notes="Stable baseline sales in North Metro."
            ),
            DemandForecast(
                product_id="PROD-COFFEE-02",
                node_id="NODE-NORTH-01",
                period="next_30_days",
                forecasted_qty=550,
                actual_run_rate_qty=560,
                trend="stable",
                notes="Consistent daily consumption in cafes & quick-commerce grocery."
            ),
            DemandForecast(
                product_id="PROD-POWER-03",
                node_id="NODE-NORTH-01",
                period="next_30_days",
                forecasted_qty=300,  # Original baseline
                actual_run_rate_qty=950,  # MASSIVE SPIKE (+216%)
                trend="spiking",
                notes="ALERT: Social media tech influencer feature sparked 3.1x surge in daily checkouts."
            ),
            DemandForecast(
                product_id="PROD-THERMOS-04",
                node_id="NODE-SOUTH-02",
                period="next_30_days",
                forecasted_qty=1100,
                actual_run_rate_qty=1150,
                trend="seasonal_high",
                notes="Winter wellness campaign driving high projected adoption."
            )
        ]
        session.add_all(forecasts)
        await session.flush()

        # 9. Scenarios representing the Assignment Scenarios
        scenarios = [
            Scenario(
                id="scenario_1",
                scenario_number=1,
                title="Scenario 1: Purchase Recommendation Review",
                scenario_type="recommendation_review",
                description="The legacy automated MRP system recommends buying 800 units of AeroWireless Pro Earbuds. The agent must investigate current inventory (320), open POs (200), demand (600), storage capacity (1000 max), and budget to decide whether to accept, modify, or reject.",
                product_id="PROD-EARBUDS-01",
                node_id="NODE-NORTH-01",
                initial_recommendation={
                    "recommended_action": "create_po",
                    "quantity": 800,
                    "supplier_id": "SUP-01",
                    "unit_cost": 45.0,
                    "total_cost": 36000.0,
                    "system_rationale": "Automated replenishment batch recommendation based on seasonal factor."
                },
                status="pending_review"
            ),
            Scenario(
                id="scenario_2",
                scenario_number=2,
                title="Scenario 2: Supplier Cannot Fulfil Purchase Order",
                scenario_type="supplier_shortfall",
                description="Purchase order PO-9041 was issued for 500 units of Organic Coffee, but Supplier SUP-02 reported they can only supply 250 units. Current stock is 80 (below safety stock 120) with 550 monthly demand. The agent must investigate alternatives and prevent a catastrophic stockout.",
                product_id="PROD-COFFEE-02",
                node_id="NODE-NORTH-01",
                initial_recommendation={
                    "current_po_id": "PO-9041",
                    "original_qty": 500,
                    "supplier_confirmed_qty": 250,
                    "shortfall_qty": 250,
                    "supplier_id": "SUP-02",
                    "system_rationale": "Supplier communicated 50% fulfillment constraint due to harvest bottlenecks."
                },
                status="pending_review"
            ),
            Scenario(
                id="scenario_3",
                scenario_number=3,
                title="Scenario 3: Demand Forecast Surge / Run-rate Anomaly",
                scenario_type="demand_spike",
                description="Demand for UltraFast Power Banks has spiked from 300 to 950 units/month (+216%). Existing stock (120) and open PO-9088 (300) total only 420 units, running out in ~13 days against a 10-day supplier lead time. The agent must evaluate the gap and execute an expedited order.",
                product_id="PROD-POWER-03",
                node_id="NODE-NORTH-01",
                initial_recommendation={
                    "baseline_forecast": 300,
                    "detected_run_rate": 950,
                    "days_of_inventory_left": 13,
                    "system_rationale": "Run-rate anomaly detector flagged stockout hazard within 14 days."
                },
                status="pending_review"
            ),
            Scenario(
                id="scenario_4",
                scenario_number=4,
                title="Scenario 4: Purchasing Multi-Constraint Conflict",
                scenario_type="purchasing_constraint",
                description="Marketing wants to purchase 1,200 units of Smart Thermos Bottles ($36,000) for campaign launch. However, available node budget is only $22,000 and available shelf storage is only 600 units. The agent must resolve the conflict intelligently rather than failing or blindly purchasing.",
                product_id="PROD-THERMOS-04",
                node_id="NODE-SOUTH-02",
                initial_recommendation={
                    "requested_qty": 1200,
                    "unit_cost": 30.0,
                    "total_cost": 36000.0,
                    "available_budget": 22000.0,
                    "available_storage": 600,
                    "system_rationale": "Unchecked manual campaign requisition violating budget and spatial limits."
                },
                status="pending_review"
            )
        ]
        session.add_all(scenarios)
        await session.commit()
        print("Database seeded successfully with all 4 scenarios!")

if __name__ == "__main__":
    asyncio.run(seed_data())
