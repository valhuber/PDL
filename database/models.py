# coding: utf-8
import datetime
from sqlalchemy import DECIMAL, DateTime, func  # API Logic Server GenAI assist
from sqlalchemy import Column, DECIMAL, Date, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

########################################################################################################################
# Classes describing database for SqlAlchemy ORM, initially created by schema introspection.
#
# Alter this file per your database maintenance policy
#    See https://apilogicserver.github.io/Docs/Project-Rebuild/#rebuilding
#
# Created:  February 05, 2025 14:26:18
# Database: sqlite:////tmp/tmp.MSPRc3WidA-01JKB807WMNRKECY2F1ZRGE935/OrderManagementSystem/database/db.sqlite
# Dialect:  sqlite
#
# mypy: ignore-errors
########################################################################################################################
 
from database.system.SAFRSBaseX import SAFRSBaseX, TestBase
from flask_login import UserMixin
import safrs, flask_sqlalchemy, os
from safrs import jsonapi_attr
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.sqltypes import NullType
from typing import List

db = SQLAlchemy() 
Base = declarative_base()  # type: flask_sqlalchemy.model.DefaultMeta
metadata = Base.metadata

#NullType = db.String  # datatype fixup
#TIMESTAMP= db.TIMESTAMP

from sqlalchemy.dialects.sqlite import *

if os.getenv('APILOGICPROJECT_NO_FLASK') is None or os.getenv('APILOGICPROJECT_NO_FLASK') == 'None':
    Base = SAFRSBaseX   # enables rules to be used outside of Flask, e.g., test data loading
else:
    Base = TestBase     # ensure proper types, so rules work for data loading
    print('*** Models.py Using TestBase ***')



class Customer(Base):  # type: ignore
    """
    description: Represents a customer in the system with unique name, balance, and credit limit attributes.
    """
    __tablename__ = 'customer'
    _s_collection_name = 'Customer'  # type: ignore

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    balance : DECIMAL = Column(DECIMAL)
    credit_limit : DECIMAL = Column(DECIMAL)

    # parent relationships (access parent)

    # child relationships (access children)
    OrderList : Mapped[List["Order"]] = relationship(back_populates="customer")



class Product(Base):  # type: ignore
    """
    description: Represents a product available in the system with a unit price.
    """
    __tablename__ = 'product'
    _s_collection_name = 'Product'  # type: ignore

    id = Column(Integer, primary_key=True)
    name = Column(String)
    unit_price : DECIMAL = Column(DECIMAL)
    count_suppliers = Column(Integer)

    # parent relationships (access parent)

    # child relationships (access children)
    ItemList : Mapped[List["Item"]] = relationship(back_populates="product")
    ProductSupplierList : Mapped[List["ProductSupplier"]] = relationship(back_populates="product")
    SysSupplierReqList : Mapped[List["SysSupplierReq"]] = relationship(back_populates="product")



class Supplier(Base):  # type: ignore
    """
    description: Represents a supplier that can provide products to the system.
    """
    __tablename__ = 'supplier'
    _s_collection_name = 'Supplier'  # type: ignore

    id = Column(Integer, primary_key=True)
    name = Column(String)
    contact_name = Column(String)
    phone = Column(String)
    email = Column(String)
    region = Column(String)

    # parent relationships (access parent)

    # child relationships (access children)
    ProductSupplierList : Mapped[List["ProductSupplier"]] = relationship(back_populates="supplier")
    SysSupplierReqList : Mapped[List["SysSupplierReq"]] = relationship(back_populates="supplier")



class ProductSupplier(Base):  # type: ignore
    """
    description: Intersection table linking products to their suppliers with supply-specific information.
    """
    __tablename__ = 'product_supplier'
    _s_collection_name = 'ProductSupplier'  # type: ignore

    id = Column(Integer, primary_key=True)
    product_id = Column(ForeignKey('product.id'))
    supplier_id = Column(ForeignKey('supplier.id'))
    supplier_part_number = Column(String)
    unit_cost : DECIMAL = Column(DECIMAL)
    lead_time_days = Column(Integer)

    # parent relationships (access parent)
    product : Mapped["Product"] = relationship(back_populates=("ProductSupplierList"))
    supplier : Mapped["Supplier"] = relationship(back_populates=("ProductSupplierList"))

    # child relationships (access children)
    

class Order(Base):  # type: ignore
    """
    description: Represents an order made by a customer, including a notes field.
    """
    __tablename__ = 'order'
    _s_collection_name = 'Order'  # type: ignore

    id = Column(Integer, primary_key=True)
    customer_id = Column(ForeignKey('customer.id'))
    date_shipped = Column(Date)
    amount_total : DECIMAL = Column(DECIMAL)
    notes = Column(String)

    # parent relationships (access parent)
    customer : Mapped["Customer"] = relationship(back_populates=("OrderList"))

    # child relationships (access children)
    ItemList : Mapped[List["Item"]] = relationship(back_populates="order")



class Item(Base):  # type: ignore
    """
    description: Represents an item in an order, including quantity and pricing details.
    """
    __tablename__ = 'item'
    _s_collection_name = 'Item'  # type: ignore

    id = Column(Integer, primary_key=True)
    order_id = Column(ForeignKey('order.id'))
    product_id = Column(ForeignKey('product.id'))
    quantity = Column(Integer, nullable=False)
    unit_price : DECIMAL = Column(DECIMAL)
    amount : DECIMAL = Column(DECIMAL)

    # parent relationships (access parent)
    order : Mapped["Order"] = relationship(back_populates=("ItemList"))
    product : Mapped["Product"] = relationship(back_populates=("ItemList"))

    # child relationships (access children)
    SysSupplierReqList : Mapped[List["SysSupplierReq"]] = relationship(back_populates="item")


class SysSupplierReq(Base):  # type: ignore
    """
    description: Audit table for AI supplier selection requests and results
    """
    __tablename__ = 'sys_supplier_req'
    _s_collection_name = 'SysSupplierReq'  # type: ignore

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(ForeignKey('item.id'), nullable=True)
    product_id = Column(ForeignKey('product.id'), nullable=False)
    chosen_supplier_id = Column(ForeignKey('supplier.id'))
    chosen_unit_price : DECIMAL = Column(DECIMAL)
    request = Column(String)
    reason = Column(String)
    created_on = Column(DateTime, server_default=func.now())

    # parent relationships (access parent)
    item : Mapped["Item"] = relationship(back_populates="SysSupplierReqList")
    product : Mapped["Product"] = relationship(back_populates="SysSupplierReqList")
    supplier : Mapped["Supplier"] = relationship(back_populates="SysSupplierReqList")

    # child relationships (access children)
