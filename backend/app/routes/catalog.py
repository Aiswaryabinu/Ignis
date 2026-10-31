"""Catalog routes: categories & products CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.catalog import Category, Product
from app.schemas.catalog import (
    CategoryCreate, CategoryUpdate, CategoryOut,
    ProductCreate, ProductUpdate, ProductOut,
)
from app.utils.deps import CurrentUser

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


# ==================== Categories ====================

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(user: CurrentUser, db: Session = Depends(get_db)):
    """List all active categories for the user's company."""
    return (
        db.query(Category)
        .filter(Category.company_id == user.company_id, Category.is_active.is_(True))
        .order_by(Category.name)
        .all()
    )


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryCreate, user: CurrentUser, db: Session = Depends(get_db)):
    """Create a new category."""
    cat = Category(company_id=user.company_id, name=body.name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/categories/{cat_id}", response_model=CategoryOut)
def update_category(cat_id: UUID, body: CategoryUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update a category name."""
    cat = (
        db.query(Category)
        .filter(Category.id == cat_id, Category.company_id == user.company_id)
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.name = body.name
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(cat_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Soft-delete a category."""
    cat = (
        db.query(Category)
        .filter(Category.id == cat_id, Category.company_id == user.company_id)
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    cat.is_active = False
    db.commit()


# ==================== Products ====================

@router.get("/products", response_model=list[ProductOut])
def list_products(
    user: CurrentUser,
    db: Session = Depends(get_db),
    category_id: UUID | None = Query(None),
    search: str | None = Query(None, max_length=200),
):
    """List products with optional category and search filters."""
    q = db.query(Product).filter(
        Product.company_id == user.company_id,
        Product.is_active.is_(True),
    )
    if category_id:
        q = q.filter(Product.category_id == category_id)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    products = q.order_by(Product.name).all()

    result = []
    for p in products:
        out = ProductOut.model_validate(p)
        out.category_name = p.category.name if p.category else None
        result.append(out)
    return result


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductCreate, user: CurrentUser, db: Session = Depends(get_db)):
    """Create a new product."""
    # Validate category ownership if provided
    if body.category_id:
        cat = db.query(Category).filter(
            Category.id == body.category_id,
            Category.company_id == user.company_id,
        ).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category")

    prod = Product(
        company_id=user.company_id,
        category_id=body.category_id,
        name=body.name,
        unit=body.unit,
        price=body.price,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    out = ProductOut.model_validate(prod)
    out.category_name = prod.category.name if prod.category else None
    return out


@router.put("/products/{prod_id}", response_model=ProductOut)
def update_product(prod_id: UUID, body: ProductUpdate, user: CurrentUser, db: Session = Depends(get_db)):
    """Update an existing product."""
    prod = (
        db.query(Product)
        .filter(Product.id == prod_id, Product.company_id == user.company_id)
        .first()
    )
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    if body.category_id:
        cat = db.query(Category).filter(
            Category.id == body.category_id,
            Category.company_id == user.company_id,
        ).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category")

    prod.name = body.name
    prod.category_id = body.category_id
    prod.unit = body.unit
    prod.price = body.price
    db.commit()
    db.refresh(prod)
    out = ProductOut.model_validate(prod)
    out.category_name = prod.category.name if prod.category else None
    return out


@router.delete("/products/{prod_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(prod_id: UUID, user: CurrentUser, db: Session = Depends(get_db)):
    """Soft-delete a product."""
    prod = (
        db.query(Product)
        .filter(Product.id == prod_id, Product.company_id == user.company_id)
        .first()
    )
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    prod.is_active = False
    db.commit()
