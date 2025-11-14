# using resolved_model self.resolved_model FIXME
# created from response, to create create_db_models.sqlite, with test data
#    that is used to create project
# should run without error in manager 
#    if not, check for decimal, indent, or import issues

import decimal
import logging
import sqlalchemy
from sqlalchemy.sql import func 
from decimal import Decimal
from logic_bank.logic_bank import Rule
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, DateTime, Numeric, Boolean, Text, DECIMAL
from sqlalchemy.types import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from datetime import date   
from datetime import datetime
from typing import List


logging.getLogger('sqlalchemy.engine.Engine').disabled = True  # remove for additional logging

Base = declarative_base()  # from system/genai/create_db_models_inserts/create_db_models_prefix.py


from sqlalchemy.dialects.sqlite import *

class Customer(Base):
    """description: Represents a customer in the system with unique name, balance, and credit limit attributes."""
    __tablename__ = 'customer'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    balance = Column(DECIMAL)
    credit_limit = Column(DECIMAL)

class Order(Base):
    """description: Represents an order made by a customer, including a notes field."""
    __tablename__ = 'order'
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customer.id'))
    date_shipped = Column(Date)
    amount_total = Column(DECIMAL)
    notes = Column(String)

class Item(Base):
    """description: Represents an item in an order, including quantity and pricing details."""
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('order.id'))
    product_id = Column(Integer, ForeignKey('product.id'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL)
    amount = Column(DECIMAL)

class Product(Base):
    """description: Represents a product available in the system with a unit price."""
    __tablename__ = 'product'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    unit_price = Column(DECIMAL)


# end of model classes


try:
    
    
    # ALS/GenAI: Create an SQLite database
    import os
    mgr_db_loc = True
    if mgr_db_loc:
        print(f'creating in manager: sqlite:///system/genai/temp/create_db_models.sqlite')
        engine = create_engine('sqlite:///system/genai/temp/create_db_models.sqlite')
    else:
        current_file_path = os.path.dirname(__file__)
        print(f'creating at current_file_path: {current_file_path}')
        engine = create_engine(f'sqlite:///{current_file_path}/create_db_models.sqlite')
    Base.metadata.create_all(engine)
    
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # ALS/GenAI: Prepare for sample data
    
    
    session.commit()
    test_customer_1 = Customer(name='Customer 1', balance=150, credit_limit=1000)
    test_customer_2 = Customer(name='Customer 2', balance=275, credit_limit=750)
    test_customer_3 = Customer(name='Customer 3', balance=150, credit_limit=1500)
    test_customer_4 = Customer(name='Customer 4', balance=0, credit_limit=1200)
    test_order_1 = Order(customer_id=1, notes='Order 1 notes', amount_total=150)
    test_order_2 = Order(customer_id=2, notes='Order 2 notes', amount_total=225)
    test_order_3 = Order(customer_id=2, notes='Order 3 notes', amount_total=50)
    test_order_4 = Order(customer_id=3, notes='Order 4 notes', amount_total=150)
    test_item_1 = Item(order_id=1, product_id=1, quantity=3, unit_price=50, amount=150)
    test_item_2 = Item(order_id=2, product_id=2, quantity=2, unit_price=25, amount=50)
    test_item_3 = Item(order_id=3, product_id=3, quantity=3, unit_price=75, amount=225)
    test_item_4 = Item(order_id=4, product_id=1, quantity=3, unit_price=50, amount=150)
    test_product_1 = Product(name='Product 1', unit_price=50)
    test_product_2 = Product(name='Product 2', unit_price=25)
    test_product_3 = Product(name='Product 3', unit_price=75)
    test_product_4 = Product(name='Product 4', unit_price=100)
    
    
    
    session.add_all([test_customer_1, test_customer_2, test_customer_3, test_customer_4, test_order_1, test_order_2, test_order_3, test_order_4, test_item_1, test_item_2, test_item_3, test_item_4, test_product_1, test_product_2, test_product_3, test_product_4])
    session.commit()
    # end of test data
    
    
except Exception as exc:
    print(f'Test Data Error: {exc}')
