"""
지식 검색 및 필터링 시스템
TASK_005: 검색/필터링 및 캐싱 메커니즘
"""

import json
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import psycopg
from functools import lru_cache
import re


class KnowledgeSearchEngine:
    """지식 베이스 검색 엔진"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.cache = {}  # 쿼리 결과 캐시
        self.cache_ttl = 300  # 5분 TTL
        self.cache_timestamps = {}
        
    def _get_cache_key(self, query: str, filters: Dict = None) -> str:
        """캐시 키 생성"""
        cache_data = f"{query}:{json.dumps(filters or {}, sort_keys=True)}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.cache_timestamps:
            return False
        
        timestamp = self.cache_timestamps[cache_key]
        return (datetime.now() - timestamp).seconds < self.cache_ttl
    
    async def search(self, 
                    query: str,
                    content_type: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    min_priority: Optional[int] = None,
                    min_confidence: Optional[float] = None,
                    limit: int = 10,
                    use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        지식 검색
        
        Args:
            query: 검색 쿼리
            content_type: 콘텐츠 타입 필터
            tags: 태그 필터
            min_priority: 최소 우선순위
            min_confidence: 최소 신뢰도
            limit: 결과 제한
            use_cache: 캐시 사용 여부
            
        Returns:
            검색 결과 리스트
        """
        
        # 캐시 확인
        filters = {
            'content_type': content_type,
            'tags': tags,
            'min_priority': min_priority,
            'min_confidence': min_confidence,
            'limit': limit
        }
        
        cache_key = self._get_cache_key(query, filters)
        
        if use_cache and self._is_cache_valid(cache_key):
            print(f"[CACHE HIT] Query: {query[:30]}...")
            return self.cache[cache_key]
        
        # DB 검색
        results = await self._search_database(
            query, content_type, tags, min_priority, min_confidence, limit
        )
        
        # 캐시 저장
        if use_cache:
            self.cache[cache_key] = results
            self.cache_timestamps[cache_key] = datetime.now()
            print(f"[CACHE MISS] Query: {query[:30]}... ({len(results)} results cached)")
        
        return results
    
    async def _search_database(self,
                              query: str,
                              content_type: Optional[str],
                              tags: Optional[List[str]],
                              min_priority: Optional[int],
                              min_confidence: Optional[float],
                              limit: int) -> List[Dict[str, Any]]:
        """데이터베이스에서 검색"""
        
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
                            confidence_score,
                            created_at,
                            updated_at
                        FROM ai_knowledge_base
                        WHERE 1=1
                    """
                    params = []
                    
                    # 텍스트 검색 (ILIKE 사용)
                    if query:
                        sql += " AND (content ILIKE %s OR w5h1_data::text ILIKE %s)"
                        search_pattern = f"%{query}%"
                        params.extend([search_pattern, search_pattern])
                    
                    # 콘텐츠 타입 필터
                    if content_type:
                        sql += " AND content_type = %s"
                        params.append(content_type)
                    
                    # 태그 필터 (ANY 연산자 사용)
                    if tags:
                        sql += " AND tags && %s"  # 배열 겹침 연산자
                        params.append(tags)
                    
                    # 우선순위 필터
                    if min_priority is not None:
                        sql += " AND priority >= %s"
                        params.append(min_priority)
                    
                    # 신뢰도 필터
                    if min_confidence is not None:
                        sql += " AND confidence_score >= %s"
                        params.append(min_confidence)
                    
                    # 정렬 및 제한
                    sql += " ORDER BY priority DESC, confidence_score DESC, updated_at DESC"
                    sql += " LIMIT %s"
                    params.append(limit)
                    
                    # 실행
                    await cur.execute(sql, params)
                    rows = await cur.fetchall()
                    
                    # 결과 변환
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
                            'confidence_score': row[7],
                            'created_at': row[8].isoformat() if row[8] else None,
                            'updated_at': row[9].isoformat() if row[9] else None,
                            'relevance_score': 0.0  # 관련성 점수 계산
                        }
                        
                        # 관련성 점수 계산
                        if query:
                            result['relevance_score'] = self._calculate_relevance(
                                query, result['content'], result.get('w5h1_data', {})
                            )
                        
                        results.append(result)
                    
                    # 관련성 순으로 재정렬
                    if query:
                        results.sort(key=lambda x: x['relevance_score'], reverse=True)
                    
                    return results
                    
        except Exception as e:
            print(f"[ERROR] Database search failed: {e}")
            return []
    
    def _calculate_relevance(self, query: str, content: str, w5h1_data: Dict) -> float:
        """관련성 점수 계산"""
        score = 0.0
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 정확한 매치
        if query_lower in content_lower:
            score += 1.0
        
        # 단어별 매치
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        common_words = query_words & content_words
        
        if query_words:
            score += len(common_words) / len(query_words) * 0.5
        
        # 6하원칙 데이터에서 매치
        for key, value in w5h1_data.items():
            if value and isinstance(value, str):
                if query_lower in value.lower():
                    score += 0.3
                    break
        
        return min(score, 2.0)  # 최대 2.0
    
    async def filter_by_category(self, category: str) -> List[Dict[str, Any]]:
        """카테고리별 필터링"""
        return await self.search("", content_type=category)
    
    async def filter_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """태그별 필터링"""
        return await self.search("", tags=tags)
    
    async def get_high_priority(self, min_priority: int = 7) -> List[Dict[str, Any]]:
        """고우선순위 항목 조회"""
        return await self.search("", min_priority=min_priority)
    
    async def get_high_confidence(self, min_confidence: float = 0.9) -> List[Dict[str, Any]]:
        """고신뢰도 항목 조회"""
        return await self.search("", min_confidence=min_confidence)
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        self.cache_timestamps.clear()
        print("[CACHE] Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        total_entries = len(self.cache)
        valid_entries = sum(1 for key in self.cache if self._is_cache_valid(key))
        
        return {
            'total_entries': total_entries,
            'valid_entries': valid_entries,
            'expired_entries': total_entries - valid_entries,
            'cache_size_bytes': sum(
                len(json.dumps(v).encode()) for v in self.cache.values()
            ),
            'ttl_seconds': self.cache_ttl
        }
    
    async def bulk_search(self, queries: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """대량 검색 (병렬 처리)"""
        tasks = [self.search(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        return {query: result for query, result in zip(queries, results)}
    
    async def search_with_w5h1(self, 
                              what: Optional[str] = None,
                              why: Optional[str] = None,
                              when: Optional[str] = None,
                              where: Optional[str] = None,
                              who: Optional[str] = None,
                              how: Optional[str] = None,
                              limit: int = 10) -> List[Dict[str, Any]]:
        """6하원칙 기반 검색"""
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    sql = """
                        SELECT 
                            id, content, content_type, w5h1_data, 
                            metadata, tags, priority, confidence_score
                        FROM ai_knowledge_base
                        WHERE 1=1
                    """
                    params = []
                    
                    # 6하원칙 필터
                    w5h1_filters = {
                        'what': what,
                        'why': why,
                        'when': when,
                        'where': where,
                        'who': who,
                        'how': how
                    }
                    
                    for field, value in w5h1_filters.items():
                        if value:
                            sql += f" AND w5h1_data->>'{field}' ILIKE %s"
                            params.append(f"%{value}%")
                    
                    sql += " ORDER BY priority DESC, confidence_score DESC"
                    sql += " LIMIT %s"
                    params.append(limit)
                    
                    await cur.execute(sql, params)
                    rows = await cur.fetchall()
                    
                    results = []
                    for row in rows:
                        results.append({
                            'id': row[0],
                            'content': row[1],
                            'content_type': row[2],
                            'w5h1_data': row[3] if row[3] else {},
                            'metadata': row[4] if row[4] else {},
                            'tags': row[5] if row[5] else [],
                            'priority': row[6],
                            'confidence_score': row[7]
                        })
                    
                    return results
                    
        except Exception as e:
            print(f"[ERROR] W5H1 search failed: {e}")
            return []


# 사용 예시
async def example_usage():
    """검색 엔진 사용 예시"""
    
    db_dsn = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
    search_engine = KnowledgeSearchEngine(db_dsn)
    
    # 1. 일반 검색
    results = await search_engine.search("RO 시스템", limit=5)
    print(f"일반 검색 결과: {len(results)}개")
    
    # 2. 카테고리 필터
    results = await search_engine.filter_by_category("operational_spec")
    print(f"운영 사양 카테고리: {len(results)}개")
    
    # 3. 태그 필터
    results = await search_engine.filter_by_tags(["RO", "pressure"])
    print(f"RO+pressure 태그: {len(results)}개")
    
    # 4. 우선순위 필터
    results = await search_engine.get_high_priority(min_priority=8)
    print(f"고우선순위 (8+): {len(results)}개")
    
    # 5. 6하원칙 검색
    results = await search_engine.search_with_w5h1(
        what="RO 시스템",
        why="막 효율"
    )
    print(f"6하원칙 검색: {len(results)}개")
    
    # 6. 캐시 통계
    stats = search_engine.get_cache_stats()
    print(f"캐시 통계: {stats}")
    
    # 7. 대량 검색
    queries = ["온도", "압력", "유량", "전도도"]
    bulk_results = await search_engine.bulk_search(queries)
    for query, results in bulk_results.items():
        print(f"  {query}: {len(results)}개")


if __name__ == "__main__":
    asyncio.run(example_usage())