
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Supplier(Base):
    __tablename__ = "supplier"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(120), nullable=False)
    region = sa.Column(sa.String(60))
    embargoed = sa.Column(sa.Boolean, default=False, nullable=False)

class ProductSupplier(Base):
    __tablename__ = "product_supplier"
    product_id = sa.Column(sa.Integer, sa.ForeignKey("product.id"), primary_key=True)
    supplier_id = sa.Column(sa.Integer, sa.ForeignKey("supplier.id"), primary_key=True)
    last_quote = sa.Column(sa.Numeric(12,2))
    on_time_pct = sa.Column(sa.Numeric(5,2))      # e.g., 0..100
    defect_rate = sa.Column(sa.Numeric(5,2))      # e.g., 0..100

class SysSupplierReq(Base):
    __tablename__ = "sys_supplier_req"
    id = sa.Column(sa.Integer, primary_key=True)
    order_id = sa.Column(sa.Integer, sa.ForeignKey("order.id"), index=True, nullable=False)
    request = sa.Column(sa.JSON)                  # inputs used for ranking (per-line summary)
    top_n   = sa.Column(sa.JSON)                  # ranked candidates with rationales
    chosen_supplier_id = sa.Column(sa.Integer, sa.ForeignKey("supplier.id"))
    reason = sa.Column(sa.String(500))
    created_on = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)
