"""
Category API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Category, Subcategory, VendorMapping
from app.schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    SubcategoryCreate, SubcategoryResponse,
    VendorMappingCreate, VendorMappingResponse, VendorMappingBulk
)

router = APIRouter(prefix="/categories", tags=["categories"])


# Vendor Mapping endpoints - MUST be defined before /{category_id} to avoid path conflicts
@router.get("/mappings", response_model=List[VendorMappingResponse])
def list_vendor_mappings(db: Session = Depends(get_db)):
    """Get all vendor to category mappings"""
    mappings = db.query(VendorMapping).all()
    return mappings


@router.post("/mappings", response_model=VendorMappingResponse)
def create_vendor_mapping(
    mapping_data: VendorMappingCreate,
    db: Session = Depends(get_db)
):
    """Create a vendor to category mapping"""
    mapping = VendorMapping(**mapping_data.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


@router.post("/mappings/sync")
def sync_vendor_mappings(
    data: VendorMappingBulk,
    db: Session = Depends(get_db)
):
    """
    Sync vendor mappings from iOS app.
    Format: {"VENDOR_NAME": {"category": "Food", "subcategory": "Dinner"}}
    """
    results = {"created": 0, "updated": 0, "errors": []}
    
    for vendor_keyword, mapping_info in data.mappings.items():
        category_name = mapping_info.get("category")
        subcategory_name = mapping_info.get("subcategory")
        
        if not category_name:
            results["errors"].append(f"Missing category for vendor: {vendor_keyword}")
            continue
        
        # Find or create category
        category = db.query(Category).filter(Category.name == category_name).first()
        if not category:
            category = Category(name=category_name)
            db.add(category)
            db.flush()
        
        # Find or create subcategory
        subcategory_id = None
        if subcategory_name:
            subcategory = db.query(Subcategory).filter(
                Subcategory.category_id == category.id,
                Subcategory.name == subcategory_name
            ).first()
            if not subcategory:
                subcategory = Subcategory(category_id=category.id, name=subcategory_name)
                db.add(subcategory)
                db.flush()
            subcategory_id = subcategory.id
        
        # Find or create mapping
        existing = db.query(VendorMapping).filter(
            VendorMapping.vendor_keyword == vendor_keyword.upper()
        ).first()
        
        if existing:
            existing.category_id = category.id
            existing.subcategory_id = subcategory_id
            existing.is_user_defined = True
            results["updated"] += 1
        else:
            mapping = VendorMapping(
                vendor_keyword=vendor_keyword.upper(),
                category_id=category.id,
                subcategory_id=subcategory_id,
                is_user_defined=True
            )
            db.add(mapping)
            results["created"] += 1
    
    db.commit()
    return results


@router.get("/mappings/export")
def export_vendor_mappings(db: Session = Depends(get_db)):
    """
    Export vendor mappings in iOS-compatible format.
    Returns: {"VENDOR_NAME": {"category": "Food", "subcategory": "Dinner"}}
    """
    mappings = db.query(VendorMapping).all()
    
    result = {}
    for mapping in mappings:
        category = db.query(Category).filter(Category.id == mapping.category_id).first()
        subcategory = None
        if mapping.subcategory_id:
            subcategory = db.query(Subcategory).filter(
                Subcategory.id == mapping.subcategory_id
            ).first()
        
        result[mapping.vendor_keyword] = {
            "category": category.name if category else "Others",
            "subcategory": subcategory.name if subcategory else "Others"
        }
    
    return result


@router.get("/", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """Get all categories with subcategories"""
    categories = db.query(Category).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a specific category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category_data: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category with optional subcategories"""
    # Check if name already exists
    existing = db.query(Category).filter(Category.name == category_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    
    category = Category(
        name=category_data.name,
        icon=category_data.icon,
        color=category_data.color,
        is_system=category_data.is_system
    )
    db.add(category)
    db.flush()  # Get the ID
    
    # Add subcategories if provided
    if category_data.subcategories:
        for sub_name in category_data.subcategories:
            subcategory = Subcategory(category_id=category.id, name=sub_name)
            db.add(subcategory)
    
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if category.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system category")
    
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}


# Subcategory endpoints
@router.post("/{category_id}/subcategories", response_model=SubcategoryResponse)
def create_subcategory(
    category_id: int,
    subcategory_data: SubcategoryCreate,
    db: Session = Depends(get_db)
):
    """Add a subcategory to a category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    subcategory = Subcategory(
        category_id=category_id,
        name=subcategory_data.name,
        icon=subcategory_data.icon
    )
    db.add(subcategory)
    db.commit()
    db.refresh(subcategory)
    return subcategory


