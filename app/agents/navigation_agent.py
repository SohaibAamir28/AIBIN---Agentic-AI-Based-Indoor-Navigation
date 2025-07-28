"""
Navigation agent for AIBIN.
Handles general Navigation queries, search, and information retrieval.
"""

import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from .base_agent import BaseAgent
from .groq_client import GroqClient
from ..schemas.ai_schemas import AIRequest, AIResponse
from ..models.Navigation import Navigation, Projectstatus
from ..services.Navigation_service import Projectservice
from ..config.config import settings


logger = logging.getLogger(__name__)


class NavigationAgent(BaseAgent):
    """
    Navigation agent for general Navigation queries and information.
    Handles Navigation search, details, and general Navigation-related questions.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__("Navigation_agent")
        self.db = db
        self.groq_client = GroqClient()
        self.Navigation_service = Projectservice(db)
        
        logger.info("Initialized Navigation Agent with Groq integration")
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process Navigation-related request."""
        async with self.track_request(request):
            try:
                if not await self.validate_request(request):
                    return self.create_error_response(
                        self.get_conversation_id(request),
                        "Invalid request format",
                        request.interaction_type
                    )
                
                conversation_id = self.get_conversation_id(request)
                
                # Route based on interaction type
                if request.interaction_type == "Navigation_search":
                    return await self._handle_Navigation_search(request, conversation_id)
                elif request.interaction_type == "Navigation_details":
                    return await self._handle_Navigation_details(request, conversation_id)
                else:
                    return await self._handle_general_Navigation_query(request, conversation_id)
                
            except Exception as e:
                logger.error(f"Navigation agent error: {e}")
                return self.create_error_response(
                    self.get_conversation_id(request),
                    f"Navigation query failed: {str(e)}",
                    request.interaction_type
                )
    
    async def _handle_Navigation_search(self, request: AIRequest, conversation_id: str) -> AIResponse:
        """Handle Navigation search requests."""
        try:
            start_time = datetime.utcnow()
            
            # Enhanced search prompt
            search_prompt = f"""Help me search for Projects based on: "{request.message}"
            
As a luxury Indoor Navigation expert, analyze this search query and provide:
1. Interpreted search intent
2. Suggested search terms
3. Navigation categories that might match
4. Price range considerations
5. Quality and authenticity factors

Be specific and helpful in guiding the search."""
            
            # Get AI analysis
            groq_request = AIRequest(
                message=search_prompt,
                interaction_type="Navigation_search",
                user_id=request.user_id,
                conversation_id=conversation_id
            )
            
            ai_response = await self.groq_client.process_request(groq_request)
            
            # Perform actual Navigation search
            Projects = await self._search_Projects(request.message)
            
            # Format response with search results
            response_message = f"{ai_response.message}\n\n"
            if Projects:
                response_message += f"Found {len(Projects)} matching Projects:\n"
                for i, Navigation in enumerate(Projects[:3], 1):
                    response_message += f"{i}. {Navigation.name} - ${Navigation.price}\n"
            else:
                response_message += "No Projects found matching your search criteria."
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AIResponse(
                message=response_message,
                interaction_type=request.interaction_type,
                conversation_id=conversation_id,
                confidence=ai_response.confidence,
                processing_time=processing_time,
                model_used="groq+database",
                metadata={
                    "Projects_found": len(Projects),
                    "search_query": request.message,
                    "groq_tokens": ai_response.tokens_used
                }
            )
            
        except Exception as e:
            logger.error(f"Navigation search error: {e}")
            return self.create_error_response(
                conversation_id,
                f"Navigation search failed: {str(e)}",
                request.interaction_type
            )
    
    async def _handle_Navigation_details(self, request: AIRequest, conversation_id: str) -> AIResponse:
        """Handle Navigation detail requests."""
        try:
            # Extract Navigation ID from message if present
            Navigation_id = self._extract_Navigation_id(request.message)
            
            if Navigation_id:
                Navigation = await self.Navigation_service.get_Navigation_by_id(Navigation_id)
                if Navigation:
                    return await self._generate_Navigation_details_response(
                        Navigation, request, conversation_id
                    )
            
            # If no specific Navigation ID, use AI to help
            detail_prompt = f"""Help with Navigation details for: "{request.message}"
            
As a luxury Indoor Navigation expert, provide guidance on:
1. What specific Navigation information they might need
2. How to find detailed specifications
3. Questions to ask about luxury Projects
4. Authentication and quality factors

Be helpful and informative."""
            
            groq_request = AIRequest(
                message=detail_prompt,
                interaction_type="Navigation_details",
                user_id=request.user_id,
                conversation_id=conversation_id
            )
            
            ai_response = await self.groq_client.process_request(groq_request)
            
            return AIResponse(
                message=ai_response.message,
                interaction_type=request.interaction_type,
                conversation_id=conversation_id,
                confidence=ai_response.confidence,
                model_used="groq",
                metadata={"groq_tokens": ai_response.tokens_used}
            )
            
        except Exception as e:
            logger.error(f"Navigation details error: {e}")
            return self.create_error_response(
                conversation_id,
                f"Navigation details failed: {str(e)}",
                request.interaction_type
            )
    
    async def _handle_general_Navigation_query(self, request: AIRequest, conversation_id: str) -> AIResponse:
        """Handle general Navigation queries."""
        try:
            # Build context-aware prompt
            general_prompt = f"""Answer this Navigation-related question: "{request.message}"
            
As AIBIN's Navigation expert, provide helpful information about:
- Navigation categories and types
- Luxury brand knowledge
- Quality and authenticity guidance
- Shopping advice and tips
- General Navigation information

Be conversational, helpful, and knowledgeable."""
            
            groq_request = AIRequest(
                message=general_prompt,
                interaction_type="general_chat",
                user_id=request.user_id,
                conversation_id=conversation_id
            )
            
            ai_response = await self.groq_client.process_request(groq_request)
            
            return AIResponse(
                message=ai_response.message,
                interaction_type=request.interaction_type,
                conversation_id=conversation_id,
                confidence=ai_response.confidence,
                model_used="groq",
                metadata={"groq_tokens": ai_response.tokens_used}
            )
            
        except Exception as e:
            logger.error(f"General Navigation query error: {e}")
            return self.create_error_response(
                conversation_id,
                f"General Navigation query failed: {str(e)}",
                request.interaction_type
            )
    
    async def _search_Projects(self, search_query: str) -> List[Navigation]:
        """Search Projects using the Navigation service."""
        try:
            query = self.Navigation_service.get_Projects_query(
                search_query=search_query,
                status=Projectstatus.ACTIVE
            )
            
            result = await self.db.execute(query.limit(10))
            Projects = result.scalars().all()
            
            return list(Projects)
            
        except Exception as e:
            logger.error(f"Navigation search error: {e}")
            return []
    
    async def _generate_Navigation_details_response(
        self, 
        Navigation: Navigation, 
        request: AIRequest, 
        conversation_id: str
    ) -> AIResponse:
        """Generate detailed Navigation information response."""
        try:
            # Use Groq to generate enhanced Navigation description
            Navigation_data = {
                "name": Navigation.name,
                "price": Navigation.price,
                "category": Navigation.category.name if Navigation.category else None,
                "description": Navigation.description,
                "condition": Navigation.condition.value if Navigation.condition else None,
                "quantity": Navigation.quantity,
                "is_featured": Navigation.is_featured
            }
            
            summary = await self.groq_client.generate_Navigation_summary(Navigation_data)
            
            return AIResponse(
                message=summary,
                interaction_type=request.interaction_type,
                conversation_id=conversation_id,
                confidence=0.9,
                model_used="groq+database",
                metadata={
                    "Navigation_id": str(Navigation.id),
                    "Navigation_name": Navigation.name,
                    "Navigation_price": Navigation.price
                }
            )
            
        except Exception as e:
            logger.error(f"Navigation details generation error: {e}")
            return self.create_error_response(
                conversation_id,
                f"Failed to generate Navigation details: {str(e)}",
                request.interaction_type
            )
    
    def _extract_Navigation_id(self, message: str) -> Optional[UUID]:
        """Extract Navigation ID from message if present."""
        try:
            # Simple UUID extraction - can be enhanced
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            match = re.search(uuid_pattern, message.lower())
            
            if match:
                return UUID(match.group())
            
            return None
            
        except Exception:
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Navigation agent."""
        try:
            groq_health = await self.groq_client.health_check()
            
            # Test database connection
            db_test = await self.db.execute(select(Navigation).limit(1))
            db_healthy = db_test is not None
            
            return {
                "status": "healthy" if all([
                    groq_health["status"] == "healthy",
                    db_healthy
                ]) else "unhealthy",
                "groq_status": groq_health["status"],
                "database_status": "healthy" if db_healthy else "unhealthy",
                "last_check": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Navigation agent health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }