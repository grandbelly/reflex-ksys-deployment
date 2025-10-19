"""
AI Service - Raw SQL Service Pattern (NO ORM)
Based on successful dashboard pattern
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

class AIService:
    """AI/RAG service using raw SQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_knowledge_base(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get AI knowledge base entries"""
        await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

        q = text("""
            SELECT
                id,
                category,
                title,
                content,
                metadata,
                created_at AT TIME ZONE 'UTC' AS created_at,
                updated_at AT TIME ZONE 'UTC' AS updated_at
            FROM ai_knowledge_base
            ORDER BY updated_at DESC
            LIMIT :limit
        """)

        result = await self.session.execute(q, {"limit": limit})
        rows = result.mappings().all()

        knowledge = []
        for row in rows:
            knowledge.append({
                "id": row['id'],
                "category": row['category'],
                "title": row['title'],
                "content": row['content'],
                "metadata": row['metadata'] if row['metadata'] else {},
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            })

        return knowledge

    async def search_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search knowledge base with vector similarity"""
        await self.session.execute(text("SET LOCAL statement_timeout = '10s'"))

        # Build WHERE conditions
        where_conditions = []
        params = {"query": f"%{query}%", "limit": limit}

        if category:
            where_conditions.append("category = :category")
            params["category"] = category

        where_clause = ""
        if where_conditions:
            where_clause = "AND " + " AND ".join(where_conditions)

        q = text(f"""
            SELECT
                id,
                category,
                title,
                content,
                metadata,
                created_at,
                updated_at,
                ts_rank(
                    to_tsvector('english', title || ' ' || content),
                    plainto_tsquery('english', :query_text)
                ) AS rank
            FROM ai_knowledge_base
            WHERE (title ILIKE :query OR content ILIKE :query)
            {where_clause}
            ORDER BY rank DESC, updated_at DESC
            LIMIT :limit
        """)

        params["query_text"] = query
        result = await self.session.execute(q, params)
        rows = result.mappings().all()

        results = []
        for row in rows:
            results.append({
                "id": row['id'],
                "category": row['category'],
                "title": row['title'],
                "content": row['content'],
                "metadata": row['metadata'] if row['metadata'] else {},
                "rank": float(row['rank']) if row['rank'] else 0,
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            })

        return results

    async def get_sensor_context(self, sensor_id: str) -> Dict[str, Any]:
        """Get sensor context for AI analysis"""
        await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

        # Get current value
        q_current = text("""
            SELECT
                tag_name,
                value::float AS current_value,
                ts AT TIME ZONE 'UTC' AS last_update,
                quality
            FROM influx_latest
            WHERE tag_name = :sensor_id
        """)

        current_result = await self.session.execute(q_current, {"sensor_id": sensor_id})
        current = current_result.mappings().first()

        # Get statistics
        q_stats = text("""
            SELECT
                AVG(value)::float AS avg_value,
                MIN(value)::float AS min_value,
                MAX(value)::float AS max_value,
                STDDEV(value)::float AS std_dev,
                COUNT(*) AS data_points
            FROM influx_hist
            WHERE tag_name = :sensor_id
            AND ts >= NOW() - INTERVAL '24 hours'
        """)

        stats_result = await self.session.execute(q_stats, {"sensor_id": sensor_id})
        stats = stats_result.mappings().first()

        # Get recent alarms
        q_alarms = text("""
            SELECT
                alarm_type,
                alarm_level,
                description,
                triggered_at
            FROM alarm_history
            WHERE sensor_id = :sensor_id
            AND triggered_at >= NOW() - INTERVAL '24 hours'
            ORDER BY triggered_at DESC
            LIMIT 5
        """)

        alarms_result = await self.session.execute(q_alarms, {"sensor_id": sensor_id})
        alarms = [dict(row) for row in alarms_result.mappings()]

        # Get QC rules
        q_qc = text("""
            SELECT
                min_value::float AS min_threshold,
                max_value::float AS max_threshold,
                description
            FROM influx_qc_rule
            WHERE tag_name = :sensor_id
        """)

        qc_result = await self.session.execute(q_qc, {"sensor_id": sensor_id})
        qc_rule = qc_result.mappings().first()

        return {
            "sensor_id": sensor_id,
            "current": dict(current) if current else None,
            "statistics": dict(stats) if stats else None,
            "recent_alarms": alarms,
            "qc_rule": dict(qc_rule) if qc_rule else None
        }

    async def save_chat_history(
        self,
        user_message: str,
        ai_response: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save chat history to database"""
        await self.session.execute(text("SET LOCAL statement_timeout = '2s'"))

        try:
            q = text("""
                INSERT INTO ai_chat_history
                (user_message, ai_response, metadata, created_at)
                VALUES (:user_message, :ai_response, :metadata, NOW())
            """)

            await self.session.execute(q, {
                "user_message": user_message,
                "ai_response": ai_response,
                "metadata": json.dumps(metadata) if metadata else None
            })
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            return False

    async def get_chat_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chat history"""
        await self.session.execute(text("SET LOCAL statement_timeout = '3s'"))

        q = text("""
            SELECT
                id,
                user_message,
                ai_response,
                metadata,
                created_at AT TIME ZONE 'UTC' AS created_at
            FROM ai_chat_history
            ORDER BY created_at DESC
            LIMIT :limit
        """)

        result = await self.session.execute(q, {"limit": limit})
        rows = result.mappings().all()

        history = []
        for row in rows:
            history.append({
                "id": row['id'],
                "user_message": row['user_message'],
                "ai_response": row['ai_response'],
                "metadata": row['metadata'] if row['metadata'] else {},
                "created_at": row['created_at']
            })

        # Reverse to get chronological order
        return list(reversed(history))

    async def get_ai_insights(self) -> Dict[str, Any]:
        """Get AI-generated insights about system status"""
        await self.session.execute(text("SET LOCAL statement_timeout = '5s'"))

        # Get system metrics
        q_metrics = text("""
            WITH sensor_status AS (
                SELECT
                    COUNT(*) AS total_sensors,
                    COUNT(CASE WHEN value > q.max_value OR value < q.min_value THEN 1 END) AS abnormal_sensors
                FROM influx_latest l
                LEFT JOIN influx_qc_rule q ON l.tag_name = q.tag_name
            ),
            alarm_stats AS (
                SELECT
                    COUNT(*) AS total_alarms_24h,
                    COUNT(CASE WHEN alarm_level >= 4 THEN 1 END) AS critical_alarms
                FROM alarm_history
                WHERE triggered_at >= NOW() - INTERVAL '24 hours'
            )
            SELECT
                s.total_sensors,
                s.abnormal_sensors,
                a.total_alarms_24h,
                a.critical_alarms
            FROM sensor_status s, alarm_stats a
        """)

        result = await self.session.execute(q_metrics)
        metrics = result.mappings().first()

        # Get trending sensors
        q_trending = text("""
            SELECT
                sensor_id,
                COUNT(*) AS alarm_count
            FROM alarm_history
            WHERE triggered_at >= NOW() - INTERVAL '24 hours'
            GROUP BY sensor_id
            ORDER BY alarm_count DESC
            LIMIT 3
        """)

        trending_result = await self.session.execute(q_trending)
        trending = [{"sensor": row[0], "count": row[1]} for row in trending_result]

        return {
            "metrics": dict(metrics) if metrics else {},
            "trending_sensors": trending,
            "timestamp": datetime.now().isoformat()
        }