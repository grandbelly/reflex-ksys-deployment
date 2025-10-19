"""
5W1H Agent for Structured Response Generation
6하원칙 기반 구조화된 응답 생성 에이전트
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class FiveW1HResponse:
    """6하원칙 응답 구조"""
    who: str      # 누가/무엇이
    what: str     # 무엇을
    where: str    # 어디서
    when: str     # 언제
    why: str      # 왜
    how: str      # 어떻게


class FiveW1HAgent:
    """
    6하원칙(5W1H) 기반 응답 구조화 에이전트
    모든 질의에 대해 체계적이고 완전한 답변 제공
    """

    def __init__(self):
        self.name = "5W1HAgent"

    async def process(self, context: Any) -> Any:
        """
        에이전트 컨텍스트를 6하원칙으로 구조화
        """
        # 6하원칙 추출
        response = FiveW1HResponse(
            who=self._extract_who(context),
            what=self._extract_what(context),
            where=self._extract_where(context),
            when=self._extract_when(context),
            why=self._extract_why(context),
            how=self._extract_how(context)
        )

        # 컨텍스트에 구조화된 응답 추가
        context.structured_response = self._format_response(response, context)
        context.five_w1h = response

        return context

    def _extract_who(self, context: Any) -> str:
        """WHO - 누가/무엇이 (주체 식별)"""

        # 센서 태그 추출
        sensor_tags = []

        # Dynamic RAG 데이터에서 태그 추출
        if hasattr(context, 'raw_data') and context.raw_data:
            if 'dynamic_rag_data' in context.raw_data:
                rag_data = context.raw_data['dynamic_rag_data']
                for data in rag_data:
                    tag = data.get('tag_name')
                    if tag and tag not in sensor_tags:
                        sensor_tags.append(tag)

        # 기존 센서 데이터에서 태그 추출
        if hasattr(context, 'sensor_data') and context.sensor_data:
            for sensor in context.sensor_data:
                tag = sensor.get('tag_name')
                if tag and tag not in sensor_tags:
                    sensor_tags.append(tag)

        # 언급된 센서 찾기
        if hasattr(context, 'query'):
            query = context.query.upper()
            mentioned_tags = [tag for tag in sensor_tags if tag in query]
            if mentioned_tags:
                return f"센서: {', '.join(mentioned_tags)}"

        if sensor_tags:
            return f"관련 센서: {', '.join(sensor_tags[:5])}"

        return "시스템 전체"

    def _extract_what(self, context: Any) -> str:
        """WHAT - 무엇을 (현상/상태)"""

        findings = []

        # Dynamic RAG 데이터 우선 사용
        if hasattr(context, 'raw_data') and context.raw_data:
            if 'dynamic_rag_data' in context.raw_data:
                rag_data = context.raw_data['dynamic_rag_data']
                for data in rag_data[:3]:  # 상위 3개만
                    tag = data.get('tag_name')
                    # 다양한 값 필드 확인
                    value = data.get('last_value') or data.get('avg_value') or data.get('value')
                    if tag and value is not None:
                        findings.append(f"{tag}: {value:.2f}" if isinstance(value, (int, float)) else f"{tag}: {value}")

        # 기존 센서 데이터 확인
        elif hasattr(context, 'sensor_data') and context.sensor_data:
            for sensor in context.sensor_data[:3]:  # 상위 3개만
                tag = sensor.get('tag_name')
                value = sensor.get('value')
                if tag and value is not None:
                    findings.append(f"{tag}: {value}")

        # QC 위반 확인
        if hasattr(context, 'qc_violations'):
            violations = context.qc_violations
            if violations:
                findings.append(f"QC 위반: {len(violations)}건")

        # 분석 결과
        if hasattr(context, 'analysis_result'):
            if "정상" in context.analysis_result:
                findings.append("상태: 정상")
            elif "경고" in context.analysis_result or "WARNING" in context.analysis_result:
                findings.append("상태: 경고")
            elif "위험" in context.analysis_result or "CRITICAL" in context.analysis_result:
                findings.append("상태: 위험")

        return " | ".join(findings) if findings else "데이터 수집 중"

    def _extract_where(self, context: Any) -> str:
        """WHERE - 어디서 (데이터 출처/위치)"""

        sources = []

        # Dynamic RAG 메타데이터 확인
        if hasattr(context, 'raw_data') and context.raw_data:
            if 'dynamic_rag_metadata' in context.raw_data:
                meta = context.raw_data['dynamic_rag_metadata']
                if 'view_used' in meta:
                    sources.append(f"View: {meta['view_used']}")
                sources.append("TimescaleDB (Dynamic RAG)")
            elif 'dynamic_rag_sql' in context.raw_data:
                sources.append("TimescaleDB (실시간 쿼리)")
            else:
                sources.append("TimescaleDB")
        elif hasattr(context, 'data_source'):
            sources.append(context.data_source)
        else:
            sources.append("TimescaleDB")

        # 사용된 뷰
        if hasattr(context, 'view_used'):
            sources.append(f"View: {context.view_used}")

        # 테이블
        if hasattr(context, 'research_notes'):
            notes = context.research_notes
            if isinstance(notes, dict):
                if 'sensor_data' in notes:
                    sources.append("influx_latest")
                if 'qc_rules' in notes:
                    sources.append("influx_qc_rule")

        return " → ".join(sources) if sources else "Database"

    def _extract_when(self, context: Any) -> str:
        """WHEN - 언제 (시간 정보)"""

        time_info = []

        # 현재 시간
        now = datetime.now()
        time_info.append(f"조회 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # Dynamic RAG 데이터의 타임스탬프 우선 사용
        if hasattr(context, 'raw_data') and context.raw_data:
            if 'dynamic_rag_data' in context.raw_data:
                rag_data = context.raw_data['dynamic_rag_data']
                if rag_data and len(rag_data) > 0:
                    for data in rag_data[:3]:  # 상위 3개
                        if 'timestamp' in data:
                            time_info.append(f"데이터 시각: {data['timestamp']}")
                        elif 'latest_bucket' in data:
                            time_info.append(f"집계 시각: {data['latest_bucket']}")
                        break  # 첫 번째 유효한 타임스탬프만

            # Dynamic RAG 메타데이터
            if 'dynamic_rag_metadata' in context.raw_data:
                meta = context.raw_data['dynamic_rag_metadata']
                if 'time_range' in meta:
                    time_info.append(f"시간 범위: {meta['time_range']}")
                if 'view_used' in meta:
                    time_info.append(f"데이터 소스: {meta['view_used']}")

        # 기존 센서 데이터 타임스탬프
        elif hasattr(context, 'sensor_data') and context.sensor_data:
            for sensor in context.sensor_data[:1]:  # 첫 번째만
                ts = sensor.get('ts')
                if ts:
                    if isinstance(ts, str):
                        time_info.append(f"데이터: {ts}")
                    elif hasattr(ts, 'strftime'):
                        time_info.append(f"데이터: {ts.strftime('%H:%M:%S')}")

        # 시간 범위
        if hasattr(context, 'time_range'):
            time_info.append(f"범위: {context.time_range}")
        elif hasattr(context, 'query'):
            query = context.query.lower()
            if "1시간" in query or "1 hour" in query:
                time_info.append("범위: 최근 1시간")
            elif "24시간" in query or "day" in query:
                time_info.append("범위: 최근 24시간")
            elif "주" in query or "week" in query:
                time_info.append("범위: 최근 1주")

        return " | ".join(time_info)

    def _extract_why(self, context: Any) -> str:
        """WHY - 왜 (원인 분석)"""

        reasons = []

        # QC 위반 원인
        if hasattr(context, 'qc_violations') and context.qc_violations:
            for violation in context.qc_violations[:2]:  # 상위 2개
                tag = violation.get('tag_name')
                value = violation.get('value')
                max_val = violation.get('max_val')
                min_val = violation.get('min_val')

                if value > max_val:
                    reasons.append(f"{tag}: 최대값({max_val}) 초과")
                elif value < min_val:
                    reasons.append(f"{tag}: 최소값({min_val}) 미달")

        # 도메인 지식 기반 원인
        if hasattr(context, 'research_notes'):
            notes = context.research_notes
            if isinstance(notes, dict) and 'domain_knowledge' in notes:
                knowledge = notes['domain_knowledge']
                if "냉각" in str(knowledge):
                    reasons.append("냉각 시스템 점검 필요 가능성")
                if "통신" in str(knowledge):
                    reasons.append("통신 장애 가능성")
                if "교정" in str(knowledge):
                    reasons.append("센서 교정 시기 도래")

        # 패턴 기반 원인
        if hasattr(context, 'analysis_result'):
            if "증가" in context.analysis_result:
                reasons.append("값이 지속적으로 증가하는 추세")
            elif "감소" in context.analysis_result:
                reasons.append("값이 지속적으로 감소하는 추세")
            elif "불안정" in context.analysis_result:
                reasons.append("값의 변동성이 큼")

        return " | ".join(reasons) if reasons else "정상 범위 내 동작"

    def _extract_how(self, context: Any) -> str:
        """HOW - 어떻게 (해결 방법/권장 조치)"""

        actions = []

        # QC 위반 기반 조치
        if hasattr(context, 'qc_violations') and context.qc_violations:
            critical_count = sum(1 for v in context.qc_violations
                               if v.get('value', 0) > v.get('max_val', float('inf')) * 1.5)

            if critical_count > 0:
                actions.append("1. 즉시 현장 점검 실시")
                actions.append("2. 비상 정지 검토")
            else:
                actions.append("1. 센서 값 모니터링 강화")
                actions.append("2. 정기 점검 일정 확인")

        # 도메인 지식 기반 조치
        if hasattr(context, 'research_notes'):
            notes = context.research_notes
            if isinstance(notes, dict) and 'domain_knowledge' in notes:
                knowledge = str(notes['domain_knowledge'])

                if "온도" in knowledge or "D100" in context.query:
                    actions.append("3. 냉각 시스템 작동 확인")
                if "압력" in knowledge or "D101" in context.query:
                    actions.append("3. 압력 밸브 점검")
                if "유량" in knowledge or "D102" in context.query:
                    actions.append("3. 유량계 교정 상태 확인")

        # 일반 권장사항
        if not actions:
            actions.append("1. 현재 상태 유지")
            actions.append("2. 정기 모니터링 계속")
            actions.append("3. 이상 징후 발견 시 즉시 보고")

        return "\n".join(actions)

    def _format_response(self, response: FiveW1HResponse, context: Any) -> str:
        """6하원칙 응답을 포맷팅"""

        formatted = []

        # 헤더
        formatted.append("\n## 6하원칙 기반 분석 결과\n")

        # WHO
        formatted.append(f"### [WHO] 누가/무엇이")
        formatted.append(f"{response.who}\n")

        # WHAT
        formatted.append(f"### [WHAT] 무엇을")
        formatted.append(f"{response.what}\n")

        # WHERE
        formatted.append(f"### [WHERE] 어디서")
        formatted.append(f"{response.where}\n")

        # WHEN
        formatted.append(f"### [WHEN] 언제")
        formatted.append(f"{response.when}\n")

        # WHY
        formatted.append(f"### [WHY] 왜")
        formatted.append(f"{response.why}\n")

        # HOW
        formatted.append(f"### [HOW] 어떻게")
        formatted.append(f"{response.how}\n")

        # 추가 정보
        if hasattr(context, 'review_feedback'):
            formatted.append("\n### [REVIEW] 품질 검토")
            formatted.append(context.review_feedback)

        return "\n".join(formatted)


# 테스트 함수
async def test_5w1h_agent():
    """5W1H Agent 테스트"""

    print("=" * 60)
    print("5W1H Agent Test")
    print("=" * 60)

    # 테스트 컨텍스트 생성
    class TestContext:
        def __init__(self):
            self.query = "D100 온도 센서에 문제가 있나요?"
            self.sensor_data = [
                {'tag_name': 'D100', 'value': 190.0, 'ts': datetime.now()},
                {'tag_name': 'D101', 'value': 1.0, 'ts': datetime.now()},
                {'tag_name': 'D102', 'value': 301.0, 'ts': datetime.now()}
            ]
            self.qc_violations = [
                {'tag_name': 'D100', 'value': 190.0, 'min_val': 20, 'max_val': 25},
                {'tag_name': 'D102', 'value': 301.0, 'min_val': 0, 'max_val': 200}
            ]
            self.research_notes = {
                'sensor_data': "3개 센서 데이터 수집",
                'qc_rules': "2개 QC 위반 감지",
                'domain_knowledge': "D100 온도 센서는 25도 초과 시 냉각 시스템 점검 필요"
            }
            self.analysis_result = "D100 센서 값이 정상 범위를 크게 벗어남"
            self.view_used = "influx_latest"
            self.time_range = "최근 1시간"

    # 에이전트 실행
    agent = FiveW1HAgent()
    context = TestContext()

    result = await agent.process(context)

    # 결과 출력
    print("\n[Structured Response]")
    print(result.structured_response)

    # 개별 컴포넌트 출력
    print("\n[5W1H Components]")
    print(f"WHO: {result.five_w1h.who}")
    print(f"WHAT: {result.five_w1h.what}")
    print(f"WHERE: {result.five_w1h.where}")
    print(f"WHEN: {result.five_w1h.when}")
    print(f"WHY: {result.five_w1h.why}")
    print(f"HOW:\n{result.five_w1h.how}")

    print("\n" + "=" * 60)
    print("Test completed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_5w1h_agent())