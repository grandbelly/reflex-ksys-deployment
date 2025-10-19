"""
6하원칙 지식 검색 모듈
TASK_004: 데이터베이스에서 6하원칙 지식 검색
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
import psycopg


class W5H1KnowledgeRetriever:
    """6하원칙 지식 검색기"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
    
    async def get_w5h1_knowledge(self, 
                                 query: str = None,
                                 content_type: str = None,
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """
        6하원칙 지식 검색
        
        Args:
            query: 검색 쿼리
            content_type: 컨텐츠 타입 필터
            limit: 결과 개수 제한
        
        Returns:
            6하원칙 지식 리스트
        """
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 기본 쿼리
                    sql = """
                        SELECT 
                            id,
                            content,
                            content_type,
                            w5h1_data,
                            metadata,
                            tags,
                            priority,
                            confidence_score
                        FROM ai_knowledge_base
                        WHERE is_active = true
                        AND w5h1_data IS NOT NULL
                        AND w5h1_data != '{}'::jsonb
                    """
                    
                    params = []
                    
                    # 검색 조건 추가
                    if query:
                        sql += " AND content ILIKE %s"
                        params.append(f"%{query}%")
                    
                    if content_type:
                        sql += " AND content_type = %s"
                        params.append(content_type)
                    
                    # 정렬 및 제한
                    sql += " ORDER BY priority DESC, confidence_score DESC LIMIT %s"
                    params.append(limit)
                    
                    await cur.execute(sql, params)
                    rows = await cur.fetchall()
                    
                    # 결과 포맷팅
                    results = []
                    for row in rows:
                        result = {
                            'id': row[0],
                            'content': row[1],
                            'content_type': row[2],
                            'w5h1_data': row[3] if row[3] else {},
                            'metadata': row[4] if row[4] else {},
                            'tags': row[5] if row[5] else [],
                            'priority': row[6],
                            'confidence_score': float(row[7]) if row[7] else 1.0
                        }
                        results.append(result)
                    
                    return results
                    
        except Exception as e:
            print(f"6하원칙 지식 검색 오류: {e}")
            return []
    
    async def get_w5h1_by_tags(self, tags: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """
        태그로 6하원칙 지식 검색
        
        Args:
            tags: 검색할 태그 리스트
            limit: 결과 개수 제한
        
        Returns:
            6하원칙 지식 리스트
        """
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 태그 배열 중 하나라도 포함하면 검색
                    sql = """
                        SELECT 
                            id,
                            content,
                            content_type,
                            w5h1_data,
                            metadata,
                            tags,
                            priority,
                            confidence_score
                        FROM ai_knowledge_base
                        WHERE is_active = true
                        AND w5h1_data IS NOT NULL
                        AND tags && %s
                        ORDER BY 
                            array_length(tags & %s, 1) DESC,  -- 매칭된 태그 수
                            priority DESC,
                            confidence_score DESC
                        LIMIT %s
                    """
                    
                    await cur.execute(sql, (tags, tags, limit))
                    rows = await cur.fetchall()
                    
                    results = []
                    for row in rows:
                        result = {
                            'id': row[0],
                            'content': row[1],
                            'content_type': row[2],
                            'w5h1_data': row[3] if row[3] else {},
                            'metadata': row[4] if row[4] else {},
                            'tags': row[5] if row[5] else [],
                            'priority': row[6],
                            'confidence_score': float(row[7]) if row[7] else 1.0
                        }
                        results.append(result)
                    
                    return results
                    
        except Exception as e:
            print(f"태그 기반 6하원칙 지식 검색 오류: {e}")
            return []
    
    async def merge_w5h1_data(self, knowledge_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        여러 6하원칙 데이터 병합
        
        Args:
            knowledge_list: 지식 리스트
        
        Returns:
            병합된 6하원칙 데이터
        """
        merged = {
            'what': [],
            'why': [],
            'when': [],
            'where': [],
            'who': [],
            'how': []
        }
        
        for knowledge in knowledge_list:
            w5h1 = knowledge.get('w5h1_data', {})
            
            for key in merged.keys():
                if key in w5h1 and w5h1[key]:
                    # 중복 제거하며 추가
                    if w5h1[key] not in merged[key]:
                        merged[key].append(w5h1[key])
        
        # 리스트를 문자열로 변환
        for key in merged.keys():
            if merged[key]:
                if len(merged[key]) == 1:
                    merged[key] = merged[key][0]
                else:
                    merged[key] = " / ".join(merged[key])
            else:
                merged[key] = ""
        
        return merged
    
    async def update_usage_stats(self, knowledge_ids: List[int]):
        """
        사용 통계 업데이트
        
        Args:
            knowledge_ids: 사용된 지식 ID 리스트
        """
        if not knowledge_ids:
            return
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 사용 횟수 증가 및 마지막 접근 시간 업데이트
                    sql = """
                        UPDATE ai_knowledge_base
                        SET 
                            usage_count = usage_count + 1,
                            last_accessed = CURRENT_TIMESTAMP
                        WHERE id = ANY(%s)
                    """
                    
                    await cur.execute(sql, (knowledge_ids,))
                    await conn.commit()
                    
        except Exception as e:
            print(f"사용 통계 업데이트 오류: {e}")
    
    async def get_popular_w5h1_knowledge(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        인기 있는 6하원칙 지식 조회
        
        Args:
            limit: 결과 개수 제한
        
        Returns:
            인기 지식 리스트
        """
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    sql = """
                        SELECT 
                            id,
                            content,
                            content_type,
                            w5h1_data,
                            metadata,
                            tags,
                            priority,
                            confidence_score,
                            usage_count
                        FROM ai_knowledge_base
                        WHERE is_active = true
                        AND w5h1_data IS NOT NULL
                        AND usage_count > 0
                        ORDER BY usage_count DESC, priority DESC
                        LIMIT %s
                    """
                    
                    await cur.execute(sql, (limit,))
                    rows = await cur.fetchall()
                    
                    results = []
                    for row in rows:
                        result = {
                            'id': row[0],
                            'content': row[1],
                            'content_type': row[2],
                            'w5h1_data': row[3] if row[3] else {},
                            'metadata': row[4] if row[4] else {},
                            'tags': row[5] if row[5] else [],
                            'priority': row[6],
                            'confidence_score': float(row[7]) if row[7] else 1.0,
                            'usage_count': row[8]
                        }
                        results.append(result)
                    
                    return results
                    
        except Exception as e:
            print(f"인기 지식 조회 오류: {e}")
            return []