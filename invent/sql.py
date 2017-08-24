# coding: utf-8

import datetime
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

Base = sqlalchemy.ext.declarative.declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    inventory_number = Column(String, unique=True)
    title = Column(String, nullable=False)
    owner = Column(String)
    resource_url = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    realm_id = Column(Integer, ForeignKey('realms.id'))

    realm = relationship("Realm")
    labels = relationship("Label", back_populates="item")

    def generate_inventory_number(self, format="{prefix}-{id:06X}"):
        if self.inventory_number is None:
            self.inventory_number = format.format(prefix=self.realm.prefix,
                id=self.id)
        return self.inventory_number

    @property
    def realm_name(self):
        if self.realm:
            return self.realm.name

    @property
    def realm_prefix(self):
        if self.realm:
            return self.realm.prefix

    def __repr__(self):
        return "<Item(id={item.id!r}, inventory_number={item.inventory_number!r}" \
                ", title={item.title!r}>".format(item=self)

class Realm(Base):
    __tablename__ = "realms"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    prefix = Column(String, nullable=False, unique=True)
    realm_url_base = Column(String)
    is_external = Column(Boolean, default=False)

class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True)
    label_type = Column("type", String, nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"))
    media_type = Column(String)
    attributes = Column(String, default="{}")
    url = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    item = relationship("Item", back_populates="labels")

def create_all(engine):
    Base.metadata.create_all(engine)

