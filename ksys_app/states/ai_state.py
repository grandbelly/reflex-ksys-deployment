"""
AI State - Service Pattern with Raw SQL
Based on successful dashboard pattern
"""
import reflex as rx
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from reflex.utils import console
from ..db_orm import get_async_session
from ..services.ai_service import AIService
from ..ai_engine.rag_engine import get_rag_response


class Message(Dict):
    """Message structure for chat"""
    text: str
    is_ai: bool
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class AIState(rx.State):
    """AI chat interface state management"""

    # Chat state
    messages: List[Dict[str, Any]] = []
    current_query: str = ""
    typing: bool = False

    # Knowledge base
    knowledge_entries: List[Dict[str, Any]] = []
    search_results: List[Dict[str, Any]] = []

    # System insights
    system_insights: Dict[str, Any] = {}
    sensor_context: Dict[str, Any] = {}

    # UI state
    loading: bool = False
    error: Optional[str] = None

    # RAG state
    rag_initialized: bool = False

    @rx.event(background=True)
    async def load(self):
        """Load initial data on page mount"""
        console.log("🔄 AIState.load() called")

        async with self:
            self.loading = True
            self.error = None

        try:
            # Load knowledge base and system insights
            async with get_async_session() as session:
                service = AIService(session)

                # Get knowledge base
                knowledge = await service.get_knowledge_base(limit=50)

                # Get system insights
                insights = await service.get_ai_insights()

                # Get chat history
                history = await service.get_chat_history(limit=10)

            async with self:
                self.knowledge_entries = knowledge
                self.system_insights = insights

                # Convert history to messages
                for entry in history:
                    # Add user message
                    self.messages.append({
                        "text": entry["user_message"],
                        "is_ai": False,
                        "timestamp": entry["created_at"].isoformat() if entry["created_at"] else ""
                    })
                    # Add AI response
                    self.messages.append({
                        "text": entry["ai_response"],
                        "is_ai": True,
                        "timestamp": entry["created_at"].isoformat() if entry["created_at"] else ""
                    })

                console.log(f"✅ Loaded {len(knowledge)} knowledge entries")

        except Exception as e:
            async with self:
                self.error = f"Failed to load AI data: {str(e)}"
            console.error(f"❌ AIState.load error: {e}")
        finally:
            async with self:
                self.loading = False

    @rx.event(background=True)
    async def send_message(self):
        """Send a message to AI"""
        query = self.current_query.strip()
        if not query:
            return

        console.log(f"💬 Sending message: {query}")

        # Add user message
        async with self:
            self.messages.append({
                "text": query,
                "is_ai": False,
                "timestamp": datetime.now().isoformat()
            })
            self.typing = True
            self.current_query = ""

        try:
            # Check if query is about a specific sensor
            sensor_id = self._extract_sensor_id(query)
            sensor_context = None

            if sensor_id:
                # Get sensor context
                async with get_async_session() as session:
                    service = AIService(session)
                    sensor_context = await service.get_sensor_context(sensor_id)

                async with self:
                    self.sensor_context = sensor_context

            # Get RAG response
            context = self._prepare_context(sensor_context)
            response = await get_rag_response(query, context)

            # Save to database
            async with get_async_session() as session:
                service = AIService(session)
                await service.save_chat_history(
                    user_message=query,
                    ai_response=response,
                    metadata={"sensor_id": sensor_id} if sensor_id else None
                )

            # Add AI response
            async with self:
                self.messages.append({
                    "text": response,
                    "is_ai": True,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {"sensor_id": sensor_id} if sensor_id else None
                })

            console.log("✅ AI response received")

        except Exception as e:
            async with self:
                self.messages.append({
                    "text": f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}",
                    "is_ai": True,
                    "timestamp": datetime.now().isoformat()
                })
            console.error(f"❌ Error sending message: {e}")
        finally:
            async with self:
                self.typing = False

    @rx.event(background=True)
    async def search_knowledge(self, query: str):
        """Search knowledge base"""
        if not query.strip():
            return

        console.log(f"🔍 Searching knowledge: {query}")

        async with self:
            self.loading = True

        try:
            async with get_async_session() as session:
                service = AIService(session)
                results = await service.search_knowledge(query, limit=10)

            async with self:
                self.search_results = results
                console.log(f"✅ Found {len(results)} results")

        except Exception as e:
            console.error(f"❌ Search error: {e}")
        finally:
            async with self:
                self.loading = False

    @rx.event(background=True)
    async def refresh_insights(self):
        """Refresh system insights"""
        console.log("🔄 Refreshing insights")

        try:
            async with get_async_session() as session:
                service = AIService(session)
                insights = await service.get_ai_insights()

            async with self:
                self.system_insights = insights
                console.log("✅ Insights refreshed")

        except Exception as e:
            console.error(f"❌ Failed to refresh insights: {e}")

    @rx.event
    def clear_chat(self):
        """Clear chat history"""
        self.messages = []
        self.sensor_context = {}
        console.log("🗑️ Chat cleared")

    def _extract_sensor_id(self, query: str) -> Optional[str]:
        """Extract sensor ID from query"""
        # Simple pattern matching for sensor IDs (D100, D101, etc.)
        import re
        pattern = r'\b(D\d{3})\b'
        match = re.search(pattern, query.upper())
        return match.group(1) if match else None

    def _prepare_context(self, sensor_context: Optional[Dict]) -> str:
        """Prepare context for RAG"""
        context_parts = []

        # Add system insights
        if self.system_insights:
            metrics = self.system_insights.get("metrics", {})
            context_parts.append(f"System Status: {metrics.get('total_sensors', 0)} sensors, "
                               f"{metrics.get('abnormal_sensors', 0)} abnormal, "
                               f"{metrics.get('total_alarms_24h', 0)} alarms in 24h")

        # Add sensor context if available
        if sensor_context and sensor_context.get("current"):
            current = sensor_context["current"]
            stats = sensor_context.get("statistics", {})
            context_parts.append(f"Sensor {sensor_context['sensor_id']}: "
                               f"Current={current.get('current_value', 0):.2f}, "
                               f"Avg={stats.get('avg_value', 0):.2f}, "
                               f"Min={stats.get('min_value', 0):.2f}, "
                               f"Max={stats.get('max_value', 0):.2f}")

        return "\n".join(context_parts) if context_parts else ""

    # Computed properties
    @rx.var
    def message_count(self) -> int:
        """Count of messages"""
        return len(self.messages)

    @rx.var
    def has_insights(self) -> bool:
        """Check if insights are available"""
        return bool(self.system_insights)

    @rx.var
    def abnormal_sensor_count(self) -> int:
        """Get abnormal sensor count"""
        metrics = self.system_insights.get("metrics", {})
        return metrics.get("abnormal_sensors", 0)

    @rx.var
    def critical_alarm_count(self) -> int:
        """Get critical alarm count"""
        metrics = self.system_insights.get("metrics", {})
        return metrics.get("critical_alarms", 0)

    @rx.var
    def get_parsed_sensor_data(self) -> List[Dict[str, Any]]:
        """Get parsed sensor data for visualization"""
        # Return empty list for now - can be implemented later if needed
        return []

    @rx.var
    def has_visualization_data(self) -> bool:
        """Check if there is visualization data"""
        return False  # Can be implemented later if needed

    @rx.var
    def has_correlation_heatmap(self) -> bool:
        """Check if there is correlation heatmap data"""
        return False

    @rx.var
    def has_predictive_chart(self) -> bool:
        """Check if there is predictive chart data"""
        return False

    @rx.var
    def has_trend_analysis(self) -> bool:
        """Check if there is trend analysis data"""
        return False

    @rx.var
    def visualization_heatmap_data(self) -> Dict[str, Any]:
        """Get heatmap visualization data"""
        return {}

    @rx.var
    def visualization_prediction_data(self) -> Dict[str, Any]:
        """Get prediction visualization data"""
        return {}

    @rx.var
    def visualization_trend_data(self) -> Dict[str, Any]:
        """Get trend visualization data"""
        return {}

    @rx.var
    def get_correlation_sensors(self) -> List[str]:
        """Get correlation sensor list"""
        return []

    @rx.var
    def get_correlation_values(self) -> List[List[float]]:
        """Get correlation values matrix"""
        return []

    @rx.var
    def get_prediction_timestamps(self) -> List[str]:
        """Get prediction timestamps"""
        return []

    @rx.var
    def get_prediction_actual(self) -> List[float]:
        """Get actual values for prediction"""
        return []

    @rx.var
    def get_prediction_predicted(self) -> List[float]:
        """Get predicted values"""
        return []

    @rx.var
    def get_trend_timestamps(self) -> List[str]:
        """Get trend timestamps"""
        return []

    @rx.var
    def get_trend_values(self) -> List[float]:
        """Get trend values"""
        return []

    @rx.var
    def get_trend_ma(self) -> List[float]:
        """Get trend moving average"""
        return []

    @rx.var
    def get_correlation_matrix_rows(self) -> List[Dict[str, Any]]:
        """Get correlation matrix rows"""
        return []

    @rx.var
    def get_analysis_insights(self) -> List[str]:
        """Get analysis insights"""
        return []

    @rx.var
    def get_analysis_metadata(self) -> Dict[str, Any]:
        """Get analysis metadata"""
        return {}

    @rx.var
    def get_anomalies_data(self) -> List[Dict[str, Any]]:
        """Get anomalies data"""
        return []

    @rx.var
    def get_comparison_data(self) -> List[Dict[str, Any]]:
        """Get comparison data"""
        return []

    @rx.var
    def get_correlation_summary(self) -> str:
        """Get correlation summary"""
        return ""

    @rx.var
    def get_predictions_data(self) -> List[Dict[str, Any]]:
        """Get predictions data"""
        return []

    @rx.var
    def get_trend_data(self) -> List[Dict[str, Any]]:
        """Get trend data"""
        return []

    @rx.var
    def get_violations_data(self) -> List[Dict[str, Any]]:
        """Get violations data"""
        return []

    @rx.var
    def has_anomalies(self) -> bool:
        """Check if there are anomalies"""
        return False

    @rx.var
    def has_comprehensive(self) -> bool:
        """Check if comprehensive data exists"""
        return False

    @rx.var
    def has_predictions(self) -> bool:
        """Check if predictions exist"""
        return False

    @rx.event
    def clear_messages(self):
        """Clear all messages"""
        self.messages = []

    @rx.event
    def load_initial_sensor_data(self):
        """Load initial sensor data"""
        pass  # Already handled in load() method