import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)  # Retail price / baseline cost
    storage_units_per_item = Column(Float, default=1.0)  # Volume footprint
    description = Column(Text, nullable=True)

    supplier_products = relationship("SupplierProduct", back_populates="product", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="product")
    forecasts = relationship("DemandForecast", back_populates="product")

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lead_time_days = Column(Integer, default=7)
    min_order_qty = Column(Integer, default=100)
    max_order_qty = Column(Integer, default=5000)
    reliability_score = Column(Float, default=0.95)  # 0.0 - 1.0 (on-time & in-full delivery rate)
    active = Column(Boolean, default=True)
    contact_email = Column(String, nullable=True)

    supplier_products = relationship("SupplierProduct", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    unit_cost = Column(Float, nullable=False)
    available_qty = Column(Integer, default=1000)  # Current stock at supplier
    is_preferred = Column(Boolean, default=False)

    supplier = relationship("Supplier", back_populates="supplier_products")
    product = relationship("Product", back_populates="supplier_products")

class FulfillmentNode(Base):
    __tablename__ = "fulfillment_nodes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    total_capacity = Column(Integer, default=10000)  # Max items/units it can hold
    used_capacity = Column(Integer, default=6500)

    inventories = relationship("Inventory", back_populates="node")
    budgets = relationship("Budget", back_populates="node")

class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    node_id = Column(String, ForeignKey("fulfillment_nodes.id"), nullable=False)
    current_stock = Column(Integer, default=0)
    safety_stock = Column(Integer, default=50)
    reserved_stock = Column(Integer, default=0)
    max_capacity = Column(Integer, default=1000)  # Dedicated shelf limit for this SKU

    product = relationship("Product", back_populates="inventories")
    node = relationship("FulfillmentNode", back_populates="inventories")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    node_id = Column(String, ForeignKey("fulfillment_nodes.id"), nullable=False)
    qty_ordered = Column(Integer, nullable=False)
    qty_fulfilled = Column(Integer, default=0)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, partial, fulfilled, cancelled
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expected_delivery = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")

class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    node_id = Column(String, ForeignKey("fulfillment_nodes.id"), nullable=False)
    period = Column(String, default="next_30_days")
    forecasted_qty = Column(Integer, nullable=False)
    actual_run_rate_qty = Column(Integer, nullable=False)  # Current 30-day run rate
    trend = Column(String, default="stable")  # stable, spiking, seasonal_high, declining
    notes = Column(Text, nullable=True)

    product = relationship("Product", back_populates="forecasts")

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(String, ForeignKey("fulfillment_nodes.id"), nullable=False)
    department = Column(String, default="Procurement")
    total_budget = Column(Float, default=50000.0)
    used_budget = Column(Float, default=20000.0)
    period = Column(String, default="monthly_current")

    node = relationship("FulfillmentNode", back_populates="budgets")

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.total_budget - self.used_budget)

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String, primary_key=True, index=True)
    scenario_number = Column(Integer, nullable=False)  # 1, 2, 3, 4
    title = Column(String, nullable=False)
    scenario_type = Column(String, nullable=False)  # recommendation_review, supplier_shortfall, demand_spike, purchasing_constraint
    description = Column(Text, nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    node_id = Column(String, ForeignKey("fulfillment_nodes.id"), nullable=False)
    initial_recommendation = Column(JSON, nullable=False)  # Dict with recommended qty, supplier, etc.
    status = Column(String, default="pending_review")  # pending_review, analyzing, decision_ready, approved, modified, rejected, executed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    decisions = relationship("AgentDecision", back_populates="scenario", cascade="all, delete-orphan")
    action_logs = relationship("AgentActionLog", back_populates="scenario", cascade="all, delete-orphan")

class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id = Column(String, primary_key=True, index=True)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    decision_type = Column(String, nullable=False)  # accept, modify, reject, escalate, split_order
    recommended_qty = Column(Integer, nullable=False)
    supplier_id = Column(String, nullable=True)
    reasoning = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.9)
    constraints_evaluated = Column(JSON, nullable=True)
    proposed_actions = Column(JSON, nullable=True)
    validation_status = Column(String, default="passed")  # passed, warning, failed
    validation_feedback = Column(JSON, nullable=True)
    iteration = Column(Integer, default=1)
    user_status = Column(String, default="pending")  # pending, approved, modified, rejected
    user_override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scenario = relationship("Scenario", back_populates="decisions")

class AgentActionLog(Base):
    __tablename__ = "agent_action_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)
    step_number = Column(Integer, default=1)
    step_type = Column(String, nullable=False)  # thought, tool_call, tool_result, validation_check, decision, execution
    tool_name = Column(String, nullable=True)
    tool_args = Column(JSON, nullable=True)
    content = Column(Text, nullable=False)
    meta_info = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    scenario = relationship("Scenario", back_populates="action_logs")
