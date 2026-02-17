"""
Category Schemas - Request/Response DTOs
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SubcategoryBase(BaseModel):
    """Base schema for Subcategory"""
    name: str
    icon: Optional[str] = None


class SubcategoryCreate(SubcategoryBase):
    """Schema for creating a subcategory"""
    category_id: int


class SubcategoryResponse(SubcategoryBase):
    """Schema for subcategory response"""
    id: int
    category_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    """Base schema for Category"""
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryCreate(CategoryBase):
    """Schema for creating a category"""
    is_system: bool = False
    subcategories: Optional[List[str]] = None  # List of subcategory names


class CategoryUpdate(BaseModel):
    """Schema for updating a category"""
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(CategoryBase):
    """Schema for category response"""
    id: int
    is_system: bool
    subcategories: List[SubcategoryResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class VendorMappingBase(BaseModel):
    """Base schema for VendorMapping"""
    vendor_keyword: str
    category_id: int
    subcategory_id: Optional[int] = None


class VendorMappingCreate(VendorMappingBase):
    """Schema for creating a vendor mapping"""
    is_user_defined: bool = False


class VendorMappingResponse(VendorMappingBase):
    """Schema for vendor mapping response"""
    id: int
    is_user_defined: bool
    match_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class VendorMappingBulk(BaseModel):
    """Schema for bulk vendor mappings (iOS sync)"""
    mappings: dict[str, dict]  # {"VENDOR_NAME": {"category": "Food", "subcategory": "Dinner"}}
