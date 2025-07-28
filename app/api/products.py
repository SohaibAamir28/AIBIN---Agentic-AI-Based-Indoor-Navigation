"""
Product management API endpoints for AIBIN platform.
Handles product CRUD operations, search, and recommendations.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.product import Product
from app.schemas.product_schemas import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    ProductListResponse
)
from app.services.product_service import Projectservice
from app.utils.dependencies import require_admin, optional_auth
from app.utils.pagination_utils import paginate_query, PaginationParams
from app.logging.log import logger

router = APIRouter(prefix="/Projects", tags=["Projects"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin)
):
    """
    Create a new product.
    
    This endpoint is restricted to administrators.
    """
    try:
        product_service = Projectservice(db)
        product = await product_service.create_product(product_data)
        return product
        
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID = Path(..., description="Product ID"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(optional_auth)
):
    """
    Get a specific product by ID.
    
    This endpoint is publicly accessible.
    Returns 404 if the product is not found.
    """
    try:
        product_service = Projectservice(db)
        product = await product_service.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return product
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    data: ProductUpdateRequest,
    product_id: UUID = Path(..., description="Product ID"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin)
):
    """
    Update a product.
    
    This endpoint is restricted to administrators.
    Returns 404 if the product is not found.
    """
    try:
        product_service = Projectservice(db)
        product = await product_service.update_product(product_id, data)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return product
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID = Path(..., description="Product ID"),
    permanent: bool = Query(False, description="Permanently delete product"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_admin)
):
    """
    Delete a product.
    
    This endpoint is restricted to administrators.
    Returns 404 if the product is not found.
    """
    try:
        product_service = Projectservice(db)
        success = await product_service.delete_product(product_id, permanent=permanent)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )


@router.get("/", response_model=ProductListResponse)
async def list_Projects(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str = Query(None, description="Filter by category"),
    search: str = Query(None, description="Search Projects"),
    min_price: float = Query(None, ge=0, description="Minimum price"),
    max_price: float = Query(None, ge=0, description="Maximum price"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(optional_auth)
):
    """
    List Projects with pagination and filtering.
    
    This endpoint is publicly accessible.
    
    **IMPORTANT**: This endpoint returns 200 even when no Projects are found.
    An empty list with total=0 is the correct response for "no Projects found".
    
    404 is used for:
    - GET /Projects/{id} when a specific product doesn't exist
    - When the endpoint itself doesn't exist
    
    200 with empty array is used for:
    - GET /Projects when no Projects match the criteria
    - This follows REST API best practices
    """
    try:
        product_service = Projectservice(db)
        query = product_service.get_Projects_query(
            search_query=search,
            min_price=min_price,
            max_price=max_price
        )
        
        pagination_params = PaginationParams(page=page, size=size)
        result = await paginate_query(db, query, pagination_params)
        
        # IMPORTANT: Always return 200 with empty array when no Projects found
        # This is correct REST API behavior for collection endpoints
        response = ProductListResponse(
            Projects=result.items,
            total=result.total,
            page=result.page,
            size=result.size,
            pages=result.pages,
        )
        
        logger.info(f"Listed {len(result.items)} Projects (total: {result.total})")
        return response
        
    except Exception as e:
        logger.error(f"Error listing Projects: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Projects"
        )