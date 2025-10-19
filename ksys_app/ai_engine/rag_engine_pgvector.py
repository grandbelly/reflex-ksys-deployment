"""
Enhanced RAG Engine with pg_vector
pg_vector 확장을 사용한 고성능 벡터 검색 RAG 엔진
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

from ..db import q, execute_query


class PgVectorRAGEngine:
    """pg_vector 기반 고성능 RAG 엔진"""
    
    def __init__(self, openai_api_key: str = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.knowledge_cache = []
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_dimension = 1536
        
    async def initialize(self):
        """RAG 엔진 초기화"""
        print("🚀 pg_vector RAG 엔진 초기화 중...")
        
        # 1. pg_vector 확장 확인
        await self._check_pgvector_extension()
        
        # 2. 벡터 컬럼 확인
        await self._check_vector_column()
        
        # 3. 지식베이스 캐시 업데이트
        await self._update_knowledge_cache()
        
        # 4. 벡터화되지 않은 지식 임베딩 생성
        await self._generate_missing_embeddings()
        
        print("✅ pg_vector RAG 엔진 초기화 완료!")
        
    async def _check_pgvector_extension(self):
        """pg_vector 확장 설치 확인"""
        try:
            sql = "SELECT * FROM pg_extension WHERE extname = 'vector'"
            result = await q(sql, ())
            if not result:
                print("⚠️ pg_vector 확장이 설치되지 않았습니다.")
                print("   관리자 권한으로 'CREATE EXTENSION vector;' 실행 필요")
            else:
                print("✅ pg_vector 확장 확인됨")
        except Exception as e:
            print(f"❌ pg_vector 확장 확인 실패: {e}")
            
    async def _check_vector_column(self):
        """벡터 컬럼 존재 확인"""
        try:
            sql = """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'ai_knowledge_base' 
                AND column_name = 'content_embedding'
            """
            result = await q(sql, ())
            if not result:
                print("⚠️ content_embedding 컬럼이 없습니다.")
                print("   ALTER TABLE ai_knowledge_base ADD COLUMN content_embedding vector(1536); 실행 필요")
            else:
                print("✅ content_embedding 벡터 컬럼 확인됨")
        except Exception as e:
            print(f"❌ 벡터 컬럼 확인 실패: {e}")
            
    async def _update_knowledge_cache(self):
        """지식베이스 캐시 업데이트"""
        try:
            sql = """
                SELECT id, content, content_type, metadata, created_at,
                       content_embedding IS NOT NULL as is_vectorized
                FROM ai_knowledge_base 
                ORDER BY created_at DESC
            """
            knowledge_data = await q(sql, ())
            
            if knowledge_data:
                self.knowledge_cache = knowledge_data
                vectorized_count = sum(1 for item in knowledge_data if item['is_vectorized'])
                print(f"📚 지식베이스 캐시 업데이트: {len(knowledge_data)}개 항목 (벡터화: {vectorized_count}개)")
            else:
                print("⚠️ 지식베이스가 비어있습니다.")
                
        except Exception as e:
            print(f"❌ 지식베이스 캐시 업데이트 실패: {e}")
            
    async def _generate_missing_embeddings(self):
        """벡터화되지 않은 지식의 임베딩 생성"""
        if not self.openai_client:
            print("⚠️ OpenAI API 키가 설정되지 않아 임베딩을 생성할 수 없습니다.")
            return
            
        try:
            # 벡터화되지 않은 지식 조회
            sql = """
                SELECT id, content 
                FROM ai_knowledge_base 
                WHERE content_embedding IS NULL
                LIMIT 50
            """
            unvectorized = await q(sql, ())
            
            if not unvectorized:
                print("✅ 모든 지식이 벡터화되어 있습니다.")
                return
                
            print(f"🔄 {len(unvectorized)}개 지식의 임베딩 생성 중...")
            
            for item in unvectorized:
                try:
                    # OpenAI 임베딩 생성
                    response = self.openai_client.embeddings.create(
                        input=item['content'],
                        model=self.embedding_model
                    )
                    embedding = response.data[0].embedding
                    
                    # 벡터 업데이트
                    update_sql = """
                        UPDATE ai_knowledge_base 
                        SET content_embedding = %s::vector 
                        WHERE id = %s
                    """
                    await execute_query(update_sql, (embedding, item['id']))
                    
                    print(f"  ✅ ID {item['id']}: 임베딩 생성 완료")
                    
                except Exception as e:
                    print(f"  ❌ ID {item['id']}: 임베딩 생성 실패 - {e}")
                    continue
                    
            # 캐시 재업데이트
            await self._update_knowledge_cache()
            
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            
    async def semantic_search_vector(self, query: str, top_k: int = 5, 
                                   threshold: float = 0.7) -> List[Dict[str, Any]]:
        """pg_vector를 사용한 고성능 벡터 검색"""
        
        if not self.openai_client:
            print("⚠️ OpenAI API 키가 설정되지 않아 벡터 검색을 사용할 수 없습니다.")
            return await self.semantic_search_tfidf(query, top_k)
            
        try:
            # 쿼리 임베딩 생성
            response = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            query_embedding = response.data[0].embedding
            
            # pg_vector 검색 함수 호출
            sql = """
                SELECT * FROM search_knowledge_vector(
                    %s::vector, %s, %s
                )
            """
            params = (query_embedding, threshold, top_k)
            
            results = await q(sql, params)
            
            if results:
                print(f"🔍 벡터 검색 결과: {len(results)}개 (임계값: {threshold})")
                return results
            else:
                print(f"🔍 벡터 검색 결과 없음 (임계값: {threshold})")
                return []
                
        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            # 폴백: TF-IDF 검색
            return await self.semantic_search_tfidf(query, top_k)
            
    async def semantic_search_tfidf(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """기존 TF-IDF 기반 검색 (폴백)"""
        
        if not self.knowledge_cache:
            await self._update_knowledge_cache()
            
        if not self.knowledge_cache:
            return []
            
        try:
            # 쿼리 벡터화
            query_vector = self.vectorizer.fit_transform([query])
            
            # 모든 지식 벡터화  
            texts = [item['content'] for item in self.knowledge_cache]
            knowledge_vectors = self.vectorizer.transform(texts)
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(query_vector, knowledge_vectors)[0]
            
            # 상위 K개 결과 추출
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # 최소 유사도 임계값
                    item = self.knowledge_cache[idx].copy()
                    item['similarity_score'] = float(similarities[idx])
                    results.append(item)
                    
            return results
            
        except Exception as e:
            print(f"❌ TF-IDF 검색 실패: {e}")
            return []
            
    async def hybrid_search(self, query: str, top_k: int = 5,
                           vector_weight: float = 0.7, text_weight: float = 0.3) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 텍스트)"""
        
        if not self.openai_client:
            return await self.semantic_search_tfidf(query, top_k)
            
        try:
            # 쿼리 임베딩 생성
            response = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            query_embedding = response.data[0].embedding
            
            # 하이브리드 검색 함수 호출
            sql = """
                SELECT * FROM search_knowledge_hybrid(
                    %s, %s::vector, %s, %s, %s
                )
            """
            params = (query, query_embedding, vector_weight, text_weight, top_k)
            
            results = await q(sql, params)
            
            if results:
                print(f"🔍 하이브리드 검색 결과: {len(results)}개")
                return results
            else:
                print("🔍 하이브리드 검색 결과 없음")
                return []
                
        except Exception as e:
            print(f"❌ 하이브리드 검색 실패: {e}")
            return await self.semantic_search_tfidf(query, top_k)
            
    async def search_sensor_knowledge_vector(self, sensor_tag: str, query: str, 
                                           top_k: int = 10) -> List[Dict[str, Any]]:
        """센서별 벡터 검색"""
        
        if not self.openai_client:
            return await self._search_sensor_knowledge_tfidf(sensor_tag, query, top_k)
            
        try:
            # 쿼리 임베딩 생성
            response = self.openai_client.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            query_embedding = response.data[0].embedding
            
            # 센서별 벡터 검색 함수 호출
            sql = """
                SELECT * FROM search_sensor_knowledge_vector(
                    %s, %s::vector, 0.6, %s
                )
            """
            params = (sensor_tag, query_embedding, top_k)
            
            results = await q(sql, params)
            
            if results:
                print(f"🔍 센서 {sensor_tag} 벡터 검색 결과: {len(results)}개")
                return results
            else:
                print(f"🔍 센서 {sensor_tag} 벡터 검색 결과 없음")
                return []
                
        except Exception as e:
            print(f"❌ 센서 벡터 검색 실패: {e}")
            return await self._search_sensor_knowledge_tfidf(sensor_tag, query, top_k)
            
    async def _search_sensor_knowledge_tfidf(self, sensor_tag: str, query: str, 
                                            top_k: int = 10) -> List[Dict[str, Any]]:
        """센서별 TF-IDF 검색 (폴백)"""
        
        try:
            sql = """
                SELECT id, content, content_type, metadata, created_at
                FROM ai_knowledge_base 
                WHERE metadata->>'sensor_tag' = %s 
                   OR metadata->>'primary_sensor' = %s
                   OR metadata->>'secondary_sensor' = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            params = [sensor_tag] * 3 + [top_k]
            
            results = await q(sql, params)
            return results or []
            
        except Exception as e:
            print(f"❌ 센서 TF-IDF 검색 실패: {e}")
            return []
            
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """지식베이스 통계 조회"""
        try:
            sql = "SELECT * FROM knowledge_base_stats"
            stats = await q(sql, ())
            
            # 벡터 품질 검증
            quality_sql = "SELECT * FROM validate_vector_quality()"
            quality = await q(quality_sql, ())
            
            return {
                "stats": stats,
                "quality": quality,
                "total_cache": len(self.knowledge_cache),
                "vectorized_cache": sum(1 for item in self.knowledge_cache if item.get('is_vectorized', False))
            }
            
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
            return {}
            
    async def optimize_vector_indexes(self):
        """벡터 인덱스 최적화"""
        try:
            print("🔧 벡터 인덱스 최적화 중...")
            
            # 인덱스 통계 수집
            sql = "ANALYZE ai_knowledge_base"
            await execute_query(sql, ())
            
            # 벡터 인덱스 재구축 (필요시)
            sql = "REINDEX INDEX CONCURRENTLY idx_ai_knowledge_vector"
            await execute_query(sql, ())
            
            print("✅ 벡터 인덱스 최적화 완료!")
            
        except Exception as e:
            print(f"❌ 인덱스 최적화 실패: {e}")
            
    async def cleanup_old_embeddings(self, days: int = 30):
        """오래된 임베딩 정리"""
        try:
            print(f"🧹 {days}일 이상 된 임베딩 정리 중...")
            
            sql = """
                UPDATE ai_knowledge_base 
                SET content_embedding = NULL 
                WHERE updated_at < NOW() - INTERVAL '%s days'
                AND content_embedding IS NOT NULL
            """
            await execute_query(sql, (days,))
            
            print("✅ 오래된 임베딩 정리 완료!")
            
        except Exception as e:
            print(f"❌ 임베딩 정리 실패: {e}")


# 사용 예시
async def test_pgvector_rag():
    """pg_vector RAG 엔진 테스트"""
    
    # OpenAI API 키 설정 필요
    openai_api_key = "your-api-key-here"
    
    rag_engine = PgVectorRAGEngine(openai_api_key)
    
    # 초기화
    await rag_engine.initialize()
    
    # 벡터 검색 테스트
    query = "온도 센서 D100의 정상 범위는?"
    results = await rag_engine.semantic_search_vector(query, top_k=3)
    
    print(f"🔍 검색 결과: {len(results)}개")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['content'][:100]}... (유사도: {result.get('similarity', 'N/A'):.3f})")
        
    # 통계 조회
    stats = await rag_engine.get_knowledge_stats()
    print(f"📊 지식베이스 통계: {stats}")


if __name__ == "__main__":
    asyncio.run(test_pgvector_rag())

