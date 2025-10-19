"""
Advanced GraphRAG Engine with Vector Embeddings and Relationship Mapping
고급 GraphRAG 엔진 - 벡터 임베딩과 관계형 검색의 융합
"""

import asyncio
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import openai
from openai import AsyncOpenAI

# Database and existing modules
from ..db import q, execute_query
from ..queries.latest import latest_snapshot
from ..queries.qc import qc_rules


class GraphRAGEngine:
    """고급 GraphRAG 엔진 - 지식 그래프와 벡터 검색의 융합"""

    def __init__(self):
        self.openai_client = None
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_cache = {}
        self.knowledge_graph = {}  # 센서 간 관계 그래프
        self.similarity_threshold = 0.75

    async def initialize(self):
        """GraphRAG 엔진 초기화"""
        # 환경변수 명시적 로드
        import os
        from dotenv import load_dotenv
        load_dotenv()

        # OpenAI 클라이언트 초기화
        from ..utils.secure_config import get_api_key_manager
        api_manager = get_api_key_manager()
        api_key = api_manager.get_openai_key()

        # 환경변수에서 직접 확인도 시도
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            print(f"🔍 환경변수에서 직접 로드 시도: {'✅ 성공' if api_key else '❌ 실패'}")

        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
            print("✅ GraphRAG OpenAI 클라이언트 초기화 완료")
        else:
            print("⚠️ OpenAI API 키가 없습니다. 벡터 임베딩 기능이 제한됩니다.")

        # 지식 그래프 구축
        await self._build_knowledge_graph()

        # 임베딩 업데이트
        await self._update_embeddings()

        print("🕸️ GraphRAG 엔진 초기화 완료")

    async def _build_knowledge_graph(self):
        """센서 간 관계 기반 지식 그래프 구축"""
        print("🕸️ 지식 그래프 구축 중...")

        # 센서 관계 정의 (실제 산업 시스템 기반)
        sensor_relationships = {
            "D100": {  # 온도 센서
                "correlates_with": ["D300"],  # 전력과 상관관계
                "affects": ["D101"],  # 온도가 압력에 영향
                "sensor_type": "temperature",
                "process_group": "thermal_management"
            },
            "D101": {  # 압력 센서
                "correlates_with": ["D102"],  # 압력-유량 연동
                "affected_by": ["D100"],  # 온도에 영향받음
                "sensor_type": "pressure",
                "process_group": "flow_control"
            },
            "D102": {  # 유량 센서
                "correlates_with": ["D101"],  # 압력과 연동
                "sensor_type": "flow",
                "process_group": "flow_control"
            },
            "D200": {  # 진동 센서 시리즈
                "correlates_with": ["D300"],  # 진동-전력 효율성
                "sensor_type": "vibration",
                "process_group": "mechanical_health"
            },
            "D201": {
                "correlates_with": ["D200", "D202"],
                "sensor_type": "vibration",
                "process_group": "mechanical_health"
            },
            "D202": {
                "correlates_with": ["D200", "D201"],
                "sensor_type": "vibration",
                "process_group": "mechanical_health"
            },
            "D300": {  # 전력 센서 시리즈
                "correlates_with": ["D100", "D200"],  # 온도, 진동과 상관관계
                "sensor_type": "power",
                "process_group": "efficiency_monitoring"
            },
            "D301": {
                "correlates_with": ["D300", "D302"],
                "sensor_type": "power",
                "process_group": "efficiency_monitoring"
            },
            "D302": {
                "correlates_with": ["D300", "D301"],
                "sensor_type": "power",
                "process_group": "efficiency_monitoring"
            }
        }

        self.knowledge_graph = sensor_relationships
        print(f"🕸️ 지식 그래프 구축 완료: {len(sensor_relationships)}개 노드")

    async def _update_embeddings(self):
        """데이터베이스의 모든 지식에 대한 임베딩 생성/업데이트"""
        if not self.openai_client:
            print("⚠️ OpenAI 클라이언트 없음 - 임베딩 업데이트 스킵")
            return

        print("🔢 임베딩 업데이트 시작...")

        # 1. knowledge_base 테이블 임베딩
        kb_sql = "SELECT id, content FROM ai_engine.knowledge_base WHERE embedding IS NULL"
        kb_records = await q(kb_sql, ())

        if kb_records:
            for record in kb_records:
                try:
                    embedding = await self._generate_embedding(record['content'])
                    if embedding:
                        update_sql = "UPDATE ai_engine.knowledge_base SET embedding = %s WHERE id = %s"
                        await execute_query(update_sql, (embedding, record['id']))
                        print(f"   ✅ KB 임베딩 업데이트: ID {record['id']}")
                except Exception as e:
                    print(f"   ❌ KB 임베딩 실패: ID {record['id']} - {e}")

        # 2. sensor_knowledge 테이블 임베딩
        sk_sql = "SELECT id, content FROM ai_engine.sensor_knowledge WHERE embedding IS NULL"
        sk_records = await q(sk_sql, ())

        if sk_records:
            for record in sk_records:
                try:
                    embedding = await self._generate_embedding(record['content'])
                    if embedding:
                        update_sql = "UPDATE ai_engine.sensor_knowledge SET embedding = %s WHERE id = %s"
                        await execute_query(update_sql, (embedding, record['id']))
                        print(f"   ✅ SK 임베딩 업데이트: ID {record['id']}")
                except Exception as e:
                    print(f"   ❌ SK 임베딩 실패: ID {record['id']} - {e}")

        print("🔢 임베딩 업데이트 완료")

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """텍스트에 대한 임베딩 생성"""
        if not self.openai_client:
            return None

        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            return None

    async def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """벡터 기반 의미론적 검색"""
        print(f"\n🔍 벡터 검색 시작: query='{query}', top_k={top_k}")

        if not self.openai_client:
            print("⚠️ OpenAI 클라이언트 없음 - 벡터 검색 불가")
            return []

        try:
            # 쿼리 임베딩 생성
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return []

            # 벡터 유사도 검색 (PostgreSQL pg_vector)
            search_sql = """
                SELECT
                    'knowledge_base' as source_table,
                    id, content, content_type, metadata,
                    embedding <-> %s as distance,
                    1 - (embedding <-> %s) as similarity
                FROM ai_engine.knowledge_base
                WHERE embedding IS NOT NULL
                UNION ALL
                SELECT
                    'sensor_knowledge' as source_table,
                    id, content, sensor_type as content_type,
                    jsonb_build_object('sensor_tag', sensor_tag) as metadata,
                    embedding <-> %s as distance,
                    1 - (embedding <-> %s) as similarity
                FROM ai_engine.sensor_knowledge
                WHERE embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT %s
            """

            params = [query_embedding] * 4 + [top_k]
            results = await q(search_sql, params)

            # 유사도 필터링
            filtered_results = [
                r for r in (results or [])
                if r['similarity'] >= self.similarity_threshold
            ]

            print(f"🔍 벡터 검색 완료: {len(filtered_results)}개 결과 (임계값: {self.similarity_threshold})")
            return filtered_results

        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            return []

    async def graph_expand_search(self, sensor_tags: List[str]) -> List[str]:
        """그래프 기반 센서 확장 검색"""
        print(f"\n🕸️ 그래프 확장 검색: 초기 태그 {sensor_tags}")

        expanded_tags = set(sensor_tags)

        for tag in sensor_tags:
            if tag in self.knowledge_graph:
                # 연관된 센서들 추가
                correlates = self.knowledge_graph[tag].get('correlates_with', [])
                affected_by = self.knowledge_graph[tag].get('affected_by', [])
                affects = self.knowledge_graph[tag].get('affects', [])

                expanded_tags.update(correlates)
                expanded_tags.update(affected_by)
                expanded_tags.update(affects)

                print(f"   {tag} → 연관: {correlates}, 영향받음: {affected_by}, 영향줌: {affects}")

        result = list(expanded_tags)
        print(f"🕸️ 확장된 센서 태그: {result}")
        return result

    async def hybrid_search(self, query: str, sensor_tags: List[str] = None, top_k: int = 8) -> Dict[str, Any]:
        """하이브리드 검색: 벡터 + 그래프 + 구조화된 데이터"""
        print(f"\n🔍 하이브리드 검색 시작: query='{query}'")

        results = {
            "vector_results": [],
            "graph_expanded_sensors": [],
            "current_sensor_data": [],
            "qc_violations": [],
            "sensor_correlations": []
        }

        # 1. 벡터 의미론적 검색
        results["vector_results"] = await self.vector_search(query, top_k)
        print(f"   벡터 검색: {len(results['vector_results'])}개")

        # 2. 센서 태그 추출 및 그래프 확장
        if not sensor_tags:
            sensor_tags = await self._extract_sensor_tags(query)

        if sensor_tags:
            results["graph_expanded_sensors"] = await self.graph_expand_search(sensor_tags)
            print(f"   그래프 확장: {len(results['graph_expanded_sensors'])}개")

            # 3. 확장된 센서들의 현재 데이터
            for tag in results["graph_expanded_sensors"][:10]:  # 최대 10개
                sensor_data = await latest_snapshot(tag)
                if sensor_data:
                    results["current_sensor_data"].extend(sensor_data)
            print(f"   현재 데이터: {len(results['current_sensor_data'])}개")

            # 4. QC 위반 검사
            results["qc_violations"] = await self._check_qc_violations(results["graph_expanded_sensors"])
            print(f"   QC 위반: {len(results['qc_violations'])}개")

            # 5. 센서 간 상관관계 분석
            results["sensor_correlations"] = await self._analyze_sensor_correlations(results["graph_expanded_sensors"])
            print(f"   상관관계: {len(results['sensor_correlations'])}개")

        print(f"🔍 하이브리드 검색 완료")
        return results

    async def _extract_sensor_tags(self, query: str) -> List[str]:
        """쿼리에서 센서 태그 추출"""
        import re

        # D + 숫자 패턴
        pattern = r'D\d{3}'
        matches = re.findall(pattern, query.upper())

        # 키워드 기반 매핑
        keyword_mapping = {
            '온도': ['D100'],
            '압력': ['D101'],
            '유량': ['D102'],
            '진동': ['D200', 'D201', 'D202'],
            '전력': ['D300', 'D301', 'D302']
        }

        for keyword, tags in keyword_mapping.items():
            if keyword in query:
                matches.extend(tags)

        return list(set(matches))

    async def _check_qc_violations(self, sensor_tags: List[str]) -> List[Dict[str, Any]]:
        """QC 규칙 위반 검사"""
        violations = []

        for tag in sensor_tags:
            try:
                # 현재 센서 값
                current_data = await latest_snapshot(tag)
                if not current_data:
                    continue

                current_value = float(current_data[0].get('value', 0))

                # QC 규칙
                qc_data = await qc_rules(tag)
                if not qc_data:
                    continue

                qc_rule = qc_data[0]
                min_val = qc_rule.get('min_val')
                max_val = qc_rule.get('max_val')

                # 위반 검사
                if min_val and current_value < float(min_val):
                    violations.append({
                        "sensor_tag": tag,
                        "violation_type": "below_minimum",
                        "current_value": current_value,
                        "threshold": float(min_val),
                        "severity": "critical"
                    })
                elif max_val and current_value > float(max_val):
                    violations.append({
                        "sensor_tag": tag,
                        "violation_type": "above_maximum",
                        "current_value": current_value,
                        "threshold": float(max_val),
                        "severity": "critical"
                    })

            except (ValueError, TypeError, KeyError):
                continue

        return violations

    async def _analyze_sensor_correlations(self, sensor_tags: List[str]) -> List[Dict[str, Any]]:
        """센서 간 상관관계 분석"""
        correlations = []

        for tag in sensor_tags:
            if tag in self.knowledge_graph:
                graph_data = self.knowledge_graph[tag]

                # 그래프에서 정의된 관계들
                for related_tag in graph_data.get('correlates_with', []):
                    if related_tag in sensor_tags:
                        correlations.append({
                            "sensor1": tag,
                            "sensor2": related_tag,
                            "relationship_type": "correlation",
                            "strength": "strong",
                            "process_group": graph_data.get('process_group', 'unknown')
                        })

                for affected_tag in graph_data.get('affects', []):
                    if affected_tag in sensor_tags:
                        correlations.append({
                            "sensor1": tag,
                            "sensor2": affected_tag,
                            "relationship_type": "causal",
                            "direction": "affects",
                            "strength": "medium"
                        })

        return correlations

    async def generate_graph_rag_response(self, query: str) -> str:
        """GraphRAG 기반 응답 생성"""
        print(f"\n🚀 GraphRAG 응답 생성: '{query}'")

        try:
            # 하이브리드 검색으로 종합적 컨텍스트 구성
            search_results = await self.hybrid_search(query)

            # 컨텍스트 구성
            context_parts = []

            # 벡터 검색 결과
            if search_results["vector_results"]:
                context_parts.append("=== 관련 지식 (벡터 검색) ===")
                for result in search_results["vector_results"][:3]:
                    similarity = result.get('similarity', 0)
                    content = result.get('content', '')
                    context_parts.append(f"[유사도: {similarity:.2f}] {content}")

            # 현재 센서 데이터
            if search_results["current_sensor_data"]:
                context_parts.append("\n=== 현재 센서 상태 ===")
                for data in search_results["current_sensor_data"][:5]:
                    tag = data.get('tag_name', 'Unknown')
                    value = data.get('value', 'N/A')
                    ts = data.get('ts', 'N/A')
                    context_parts.append(f"- {tag}: {value} (시간: {ts})")

            # QC 위반사항
            if search_results["qc_violations"]:
                context_parts.append("\n=== QC 위반 사항 ===")
                for violation in search_results["qc_violations"]:
                    tag = violation["sensor_tag"]
                    violation_type = violation["violation_type"]
                    current = violation["current_value"]
                    threshold = violation["threshold"]
                    context_parts.append(f"🚨 {tag}: {current} ({violation_type}, 임계값: {threshold})")

            # 센서 상관관계
            if search_results["sensor_correlations"]:
                context_parts.append("\n=== 센서 상관관계 ===")
                for corr in search_results["sensor_correlations"][:3]:
                    s1, s2 = corr["sensor1"], corr["sensor2"]
                    rel_type = corr["relationship_type"]
                    context_parts.append(f"- {s1} ↔ {s2} ({rel_type})")

            context_text = "\n".join(context_parts)

            # OpenAI 응답 생성
            if self.openai_client and context_parts:
                system_prompt = """당신은 산업용 센서 모니터링 시스템의 GraphRAG AI 어시스턴트입니다.

핵심 원칙:
1. 제공된 컨텍스트 정보만 사용하여 응답
2. 벡터 검색, 현재 데이터, QC 위반, 센서 상관관계를 종합적으로 분석
3. 구체적이고 실용적인 인사이트 제공
4. 환각(hallucination) 금지 - 확실한 정보만 제공

응답 형식:
- 명확하고 구조화된 분석
- 관련 센서들 간의 연관성 설명
- 필요시 조치 사항 제안"""

                user_prompt = f"""질문: {query}

GraphRAG 컨텍스트:
{context_text}

위 정보를 바탕으로 종합적이고 정확한 분석을 제공해주세요."""

                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.1  # 매우 낮은 temperature로 환각 최소화
                )

                ai_response = response.choices[0].message.content

                # 검색 로그 기록
                await self._log_search(query, search_results, ai_response)

                return ai_response
            else:
                return "GraphRAG 분석을 위한 충분한 컨텍스트를 찾을 수 없습니다."

        except Exception as e:
            print(f"❌ GraphRAG 응답 생성 실패: {e}")
            return f"GraphRAG 분석 중 오류가 발생했습니다: {str(e)}"

    async def _log_search(self, query: str, search_results: Dict[str, Any], response: str):
        """검색 로그 기록"""
        try:
            # 쿼리 임베딩 생성
            query_embedding = await self._generate_embedding(query) if self.openai_client else None

            log_sql = """
                INSERT INTO ai_engine.rag_search_log
                (query_text, query_embedding, search_results, similarity_threshold, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """

            log_data = {
                "vector_count": len(search_results.get("vector_results", [])),
                "sensor_count": len(search_results.get("graph_expanded_sensors", [])),
                "violation_count": len(search_results.get("qc_violations", [])),
                "correlation_count": len(search_results.get("sensor_correlations", [])),
                "response_length": len(response)
            }

            await execute_query(log_sql, (
                query,
                query_embedding,
                json.dumps(log_data),
                self.similarity_threshold,
                datetime.now()
            ))

        except Exception as e:
            print(f"⚠️ 검색 로그 기록 실패: {e}")


# 전역 GraphRAG 엔진 인스턴스
graph_rag_engine = GraphRAGEngine()


async def initialize_graph_rag_engine():
    """GraphRAG 엔진 초기화"""
    await graph_rag_engine.initialize()


async def get_graph_rag_response(query: str) -> str:
    """GraphRAG 기반 응답 생성"""
    return await graph_rag_engine.generate_graph_rag_response(query)