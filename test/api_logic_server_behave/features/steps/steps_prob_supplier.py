
# Pseudo step defs — adapt to your project's fixtures/session helpers.
from behave import given, when, then
from sqlalchemy.orm import Session
from database.models import Supplier, SysSupplierReq
from database.models import Order, Item, Product  # adapt import
from datetime import date, timedelta
import json

@given("supplier S1 is embargoed and supplier S2 is not")
def step_impl(ctx):
    s1 = Supplier(id=1, name="S1", region="Suez", embargoed=True)
    s2 = Supplier(id=2, name="S2", region="Local", embargoed=False)
    ctx.session.add_all([s1, s2])

@given("rank_suppliers for Product P returns [S1(score=0.92), S2(score=0.90)]")
def step_impl(ctx):
    # If using the provided stub, scores already align; otherwise monkeypatch ranker here.
    pass

@when("an order (supplier mode) is inserted with one item P qty 5 need_by in 10 days")
def step_impl(ctx):
    need_by = date.today() + timedelta(days=10)
    o = Order(fulfillment_mode="supplier", need_by=need_by, ship_to_region="EU")
    p = ctx.session.query(Product).first()
    ctx.session.add_all([o, Item(order=o, product_id=p.id, quantity=5)])
    ctx.session.commit()
    ctx.order_id = o.id

@then("the order's supplier should be S2")
def step_impl(ctx):
    o = ctx.session.get(Order, ctx.order_id)
    assert o.supplier_id == 2

@then("there should be a SysSupplierReq row with both S1 and S2 in top_n")
def step_impl(ctx):
    row = ctx.session.query(SysSupplierReq).filter_by(order_id=ctx.order_id).one()
    ids = [r["supplier_id"] for r in row.top_n]
    assert set(ids) >= {1, 2}
