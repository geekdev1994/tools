"""
Category and VendorMapping Models
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class Category(Base):
    """Category for organizing transactions"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    icon = Column(String(10), nullable=True)  # Emoji
    color = Column(String(7), nullable=True)  # Hex color
    is_system = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subcategories = relationship("Subcategory", back_populates="category", cascade="all, delete-orphan")
    vendor_mappings = relationship("VendorMapping", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"


class Subcategory(Base):
    """Subcategory within a category"""
    __tablename__ = "subcategories"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(100), nullable=False)
    icon = Column(String(10), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="subcategories")

    def __repr__(self):
        return f"<Subcategory(id={self.id}, name={self.name})>"


class VendorMapping(Base):
    """Maps vendor keywords to categories"""
    __tablename__ = "vendor_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    vendor_keyword = Column(String(255), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)
    
    is_user_defined = Column(Boolean, default=False)
    match_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="vendor_mappings")

    def __repr__(self):
        return f"<VendorMapping(keyword={self.vendor_keyword}, category_id={self.category_id})>"
