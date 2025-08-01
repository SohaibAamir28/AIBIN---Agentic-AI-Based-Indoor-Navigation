"""
Product service for AIBIN Indoor Navigation platform.
Handles core product operations and business logic.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.product import Product
from app.schemas.product_schemas import ProductCreateRequest, ProductUpdateRequest, Projectstatus
from app.logging.log import logger


class Projectservice:
    """Service for product operations following AIBIN async patterns."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize product service.
        
        Args:
            db: Database session
        """
        self.db = db

    async def create_product(
        self,
        data: ProductCreateRequest,
        user_id: Optional[UUID] = None
    ) -> Product:
        """
        Create a new product.
        
        Args:
            data: Product data
            user_id: ID of user creating the product
            
        Returns:
            Newly created product
        """
        # Get product data and filter out fields not in the Product model
        product_data = data.model_dump(exclude_unset=True)
        
        # Define fields that are valid for the Product model
        # This prevents the 'tags' and other schema-only fields from being passed to the model
        valid_product_fields = {
            'name', 'slug', 'description', 'short_description', 'category_id',
            'price', 'compare_at_price', 'cost_price', 'currency', 'sku', 'barcode',
            'quantity', 'low_stock_threshold', 'status', 'is_featured', 'is_visible',
            'weight', 'weight_unit', 'dimensions', 'is_second_hand', 'condition',
            'condition_description', 'meta_title', 'meta_description', 'meta_keywords'
        }
        
        # Filter product data to only include valid fields
        filtered_product_data = {
            key: value for key, value in product_data.items() 
            if key in valid_product_fields
        }
        
        if user_id:
            filtered_product_data["created_by"] = user_id
            
        # Create product with filtered data
        product = Product(**filtered_product_data)
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        
        # Log creation with additional info about filtered fields
        filtered_fields = set(product_data.keys()) - set(filtered_product_data.keys())
        if filtered_fields:
            logger.info(f"Product created: {product.id} (filtered fields: {filtered_fields})")
        else:
            logger.info(f"Product created: {product.id}")
        
        return product

    async def get_product_by_id(self, product_id: UUID) -> Optional[Product]:
        """
        Get a product by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product if found, None otherwise
        """
        query = select(Product).where(
            and_(
                Product.id == product_id,
                Product.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def update_product(
        self,
        product_id: UUID, 
        data: ProductUpdateRequest
    ) -> Optional[Product]:
        """
        Update a product.
        
        Args:
            product_id: Product ID
            data: Updated product data
            
        Returns:
            Updated product if found, None otherwise
        """
        # Get product
        product = await self.get_product_by_id(product_id)
        if not product:
            return None
        
        # Get update data and filter out fields not in the Product model
        update_data = data.model_dump(exclude_unset=True)
        
        # Define fields that are valid for the Product model
        valid_product_fields = {
            'name', 'slug', 'description', 'short_description', 'category_id',
            'price', 'compare_at_price', 'cost_price', 'currency', 'sku', 'barcode',
            'quantity', 'low_stock_threshold', 'status', 'is_featured', 'is_visible',
            'weight', 'weight_unit', 'dimensions', 'is_second_hand', 'condition',
            'condition_description', 'meta_title', 'meta_description', 'meta_keywords'
        }
        
        # Filter update data to only include valid fields
        filtered_update_data = {
            key: value for key, value in update_data.items() 
            if key in valid_product_fields
        }
        
        # Update product attributes
        for key, value in filtered_update_data.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        # Always update the updated_at timestamp
        product.updated_at = datetime.utcnow()
        
        # Save changes
        await self.db.commit()
        await self.db.refresh(product)
        
        # Log update with additional info about filtered fields
        filtered_fields = set(update_data.keys()) - set(filtered_update_data.keys())
        if filtered_fields:
            logger.info(f"Product updated: {product.id} (filtered fields: {filtered_fields})")
        else:
            logger.info(f"Product updated: {product.id}")
        
        return product

    async def delete_product(
        self,
        product_id: UUID,
        permanent: bool = False
    ) -> bool:
        """
        Delete a product.
        
        Args:
            product_id: Product ID
            permanent: If True, permanently delete from database
            
        Returns:
            True if successful, False if product not found
        """
        # Get product
        product = await self.get_product_by_id(product_id)
        if not product:
            return False
        
        if permanent:
            # Hard delete
            await self.db.delete(product)
        else:
            # Soft delete
            product.is_deleted = True
            product.deleted_at = datetime.utcnow()
            product.updated_at = datetime.utcnow()
        
        # Save changes
        await self.db.commit()
        
        logger.info(f"Product deleted: {product_id} (permanent: {permanent})")
        return True

    def get_Projects_query(
        self,
        category_id: Optional[UUID] = None,
        search_query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_featured: Optional[bool] = None,
        status: Optional[Projectstatus] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Select:
        """
        Build a query for Projects with filtering.
        
        Args:
            category_id: Filter by category ID
            search_query: Search in name/description
            min_price: Minimum price filter
            max_price: Maximum price filter
            is_featured: Filter by featured status
            status: Filter by product status
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            SQLAlchemy select query
        """
        # Base query - only non-deleted Projects
        query = select(Product).where(Product.is_deleted == False)
        
        # Apply filters
        if category_id:
            query = query.where(Product.category_id == category_id)
            
        if search_query:
            search_filter = or_(
                Product.name.ilike(f"%{search_query}%"),
                Product.description.ilike(f"%{search_query}%"),
                Product.short_description.ilike(f"%{search_query}%")
            )
            query = query.where(search_filter)
            
        if min_price is not None:
            query = query.where(Product.price >= min_price)
            
        if max_price is not None:
            query = query.where(Product.price <= max_price)
            
        if is_featured is not None:
            query = query.where(Product.is_featured == is_featured)
            
        if status:
            query = query.where(Product.status == status)
            
        # Apply sorting
        sort_column = getattr(Product, sort_by, Product.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
            
        return query