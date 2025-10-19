"""
6하원칙(5W1H) 응답 포맷터
TASK_004: AI_IMPLEMENT_5W1H_FORMATTER
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class W5H1Response:
    """6하원칙 응답 구조"""
    what: str = ""      # 무엇을
    why: str = ""       # 왜
    when: str = ""      # 언제
    where: str = ""     # 어디서
    who: str = ""       # 누가
    how: str = ""       # 어떻게
    
    # 추가 메타데이터
    confidence: float = 1.0
    sources: List[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def to_markdown(self) -> str:
        """마크다운 형식으로 변환"""
        md = "## 📋 6하원칙 기반 응답\n\n"
        
        if self.what:
            md += f"### 🎯 **무엇을 (What)**\n{self.what}\n\n"
        
        if self.why:
            md += f"### 💡 **왜 (Why)**\n{self.why}\n\n"
        
        if self.when:
            md += f"### ⏰ **언제 (When)**\n{self.when}\n\n"
        
        if self.where:
            md += f"### 📍 **어디서 (Where)**\n{self.where}\n\n"
        
        if self.who:
            md += f"### 👤 **누가 (Who)**\n{self.who}\n\n"
        
        if self.how:
            md += f"### 🔧 **어떻게 (How)**\n{self.how}\n\n"
        
        if self.sources:
            md += f"### 📚 **출처**\n"
            for source in self.sources:
                md += f"- {source}\n"
            md += "\n"
        
        md += f"*신뢰도: {self.confidence:.1%} | 생성시간: {self.timestamp}*"
        
        return md
    
    def to_text(self) -> str:
        """텍스트 형식으로 변환"""
        text = "=== 6하원칙 기반 응답 ===\n\n"
        
        if self.what:
            text += f"[무엇을] {self.what}\n"
        
        if self.why:
            text += f"[왜] {self.why}\n"
        
        if self.when:
            text += f"[언제] {self.when}\n"
        
        if self.where:
            text += f"[어디서] {self.where}\n"
        
        if self.who:
            text += f"[누가] {self.who}\n"
        
        if self.how:
            text += f"[어떻게] {self.how}\n"
        
        if self.sources:
            text += f"\n[출처] {', '.join(self.sources)}\n"
        
        text += f"\n(신뢰도: {self.confidence:.1%})"
        
        return text


class W5H1Formatter:
    """6하원칙 응답 포맷터"""
    
    def __init__(self):
        # 질문 패턴 매핑
        self.question_patterns = {
            'what': [
                r'무엇|뭐|what|어떤.*것|뭘',
                r'센서.*값|데이터|상태|결과|내용'
            ],
            'why': [
                r'왜|이유|원인|why|때문',
                r'어째서|어떻게.*해서'
            ],
            'when': [
                r'언제|시간|날짜|when|몇시|며칠',
                r'주기|빈도|간격|타이밍'
            ],
            'where': [
                r'어디|위치|장소|where|곳',
                r'지점|구역|섹션|부분'
            ],
            'who': [
                r'누가|누구|담당|who|책임자',
                r'운영자|관리자|엔지니어'
            ],
            'how': [
                r'어떻게|방법|how|절차|과정',
                r'방식|수단|기법|프로세스'
            ]
        }
        
        # 도메인별 템플릿
        self.domain_templates = {
            'sensor': {
                'what': '센서 {tag_name}의 현재 값은 {value}{unit}입니다',
                'why': '이 센서는 {purpose}를 모니터링하기 위해 설치되었습니다',
                'when': '{timestamp}에 측정되었습니다',
                'where': '{location}에 위치한 센서입니다',
                'who': '시스템이 자동으로 모니터링합니다',
                'how': '{method} 방식으로 측정합니다'
            },
            'alarm': {
                'what': '{alarm_type} 경보가 발생했습니다',
                'why': '{trigger_reason} 때문에 발생했습니다',
                'when': '{alarm_time}에 감지되었습니다',
                'where': '{alarm_location}에서 발생했습니다',
                'who': '운영팀에 자동 통보되었습니다',
                'how': '정해진 대응 절차에 따라 처리해야 합니다'
            },
            'maintenance': {
                'what': '{equipment} 정비 작업입니다',
                'why': '{maintenance_reason}를 위해 필요합니다',
                'when': '{schedule}에 수행됩니다',
                'where': '{location}에서 작업합니다',
                'who': '{team} 팀이 담당합니다',
                'how': '{procedure}에 따라 진행합니다'
            }
        }
    
    def analyze_question(self, question: str) -> Dict[str, bool]:
        """질문 분석 - 어떤 W/H가 필요한지 파악"""
        needs = {}
        
        for category, patterns in self.question_patterns.items():
            needs[category] = any(
                re.search(pattern, question, re.IGNORECASE) 
                for pattern in patterns
            )
        
        # 아무것도 매치되지 않으면 모두 필요
        if not any(needs.values()):
            needs = {k: True for k in needs}
        
        return needs
    
    def extract_from_text(self, text: str, context: Dict[str, Any] = None) -> W5H1Response:
        """텍스트에서 6하원칙 정보 추출"""
        response = W5H1Response()
        
        # 컨텍스트에서 정보 추출
        if context:
            # What - 주요 내용
            if 'current_data' in context:
                data_summary = self._summarize_data(context['current_data'])
                response.what = data_summary
            
            # When - 시간 정보
            if 'timestamp' in context:
                response.when = context['timestamp']
            elif 'current_data' in context and context['current_data']:
                first_data = context['current_data'][0]
                if 'ts' in first_data:
                    response.when = first_data['ts']
            
            # Where - 위치 정보
            if 'location' in context:
                response.where = context['location']
            elif 'tag_name' in context:
                response.where = f"센서 {context['tag_name']} 위치"
            
            # Who - 담당자 정보
            response.who = context.get('responsible', '시스템 자동 관리')
            
            # Why - 이유/원인
            if 'reason' in context:
                response.why = context['reason']
            
            # How - 방법/절차
            if 'method' in context:
                response.how = context['method']
        
        # 텍스트 파싱으로 보완
        response = self._parse_text_content(text, response)
        
        return response
    
    def _summarize_data(self, data_list: List[Dict]) -> str:
        """데이터 요약"""
        if not data_list:
            return "데이터 없음"
        
        summary_parts = []
        for data in data_list[:3]:  # 상위 3개만
            tag = data.get('tag_name', 'Unknown')
            value = data.get('value', 'N/A')
            unit = data.get('unit', '')
            summary_parts.append(f"{tag}: {value}{unit}")
        
        return ", ".join(summary_parts)
    
    def _parse_text_content(self, text: str, response: W5H1Response) -> W5H1Response:
        """텍스트 내용 파싱"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 패턴 매칭
            if not response.what and any(word in line.lower() for word in ['센서', '값', '상태', '데이터']):
                response.what = response.what or line
            
            if not response.why and any(word in line.lower() for word in ['때문', '이유', '원인']):
                response.why = response.why or line
            
            if not response.when and re.search(r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}', line):
                response.when = response.when or line
            
            if not response.where and any(word in line.lower() for word in ['위치', '지점', '구역']):
                response.where = response.where or line
            
            if not response.how and any(word in line.lower() for word in ['방법', '절차', '프로세스']):
                response.how = response.how or line
        
        return response
    
    def format_response(self, 
                       content: str,
                       question: str = None,
                       context: Dict[str, Any] = None,
                       format_type: str = 'markdown') -> str:
        """
        응답 포맷팅
        
        Args:
            content: 원본 응답 내용
            question: 사용자 질문 (선택)
            context: 컨텍스트 정보 (선택)
            format_type: 출력 형식 ('markdown', 'json', 'text')
        
        Returns:
            포맷팅된 응답
        """
        # 6하원칙 정보 추출
        w5h1_response = self.extract_from_text(content, context)
        
        # 질문 분석해서 필요한 부분만 포함
        if question:
            needs = self.analyze_question(question)
            
            # 불필요한 항목 제거
            if not needs.get('what', True):
                w5h1_response.what = ""
            if not needs.get('why', True):
                w5h1_response.why = ""
            if not needs.get('when', True):
                w5h1_response.when = ""
            if not needs.get('where', True):
                w5h1_response.where = ""
            if not needs.get('who', True):
                w5h1_response.who = ""
            if not needs.get('how', True):
                w5h1_response.how = ""
        
        # 출처 추가
        if context and 'sources' in context:
            w5h1_response.sources = context['sources']
        
        # 신뢰도 설정
        if context and 'confidence' in context:
            w5h1_response.confidence = context['confidence']
        
        # 포맷 변환
        if format_type == 'json':
            return w5h1_response.to_json()
        elif format_type == 'text':
            return w5h1_response.to_text()
        else:  # markdown (default)
            return w5h1_response.to_markdown()
    
    def apply_template(self, 
                      domain: str,
                      data: Dict[str, Any]) -> W5H1Response:
        """도메인별 템플릿 적용"""
        if domain not in self.domain_templates:
            domain = 'sensor'  # 기본값
        
        template = self.domain_templates[domain]
        response = W5H1Response()
        
        # 템플릿 적용
        for field in ['what', 'why', 'when', 'where', 'who', 'how']:
            if field in template:
                try:
                    setattr(response, field, template[field].format(**data))
                except KeyError:
                    # 데이터가 없으면 템플릿 그대로
                    setattr(response, field, template[field])
        
        return response
    
    def merge_responses(self, *responses: W5H1Response) -> W5H1Response:
        """여러 응답 병합"""
        merged = W5H1Response()
        
        for response in responses:
            # 각 필드 병합 (빈 값이 아닌 것 우선)
            for field in ['what', 'why', 'when', 'where', 'who', 'how']:
                current = getattr(merged, field)
                new = getattr(response, field)
                
                if new and not current:
                    setattr(merged, field, new)
                elif new and current and new != current:
                    # 둘 다 있으면 합치기
                    setattr(merged, field, f"{current} / {new}")
            
            # 출처 병합
            merged.sources.extend(response.sources)
        
        # 중복 제거
        merged.sources = list(set(merged.sources))
        
        # 평균 신뢰도
        confidences = [r.confidence for r in responses if r.confidence > 0]
        if confidences:
            merged.confidence = sum(confidences) / len(confidences)
        
        return merged
    
    def format_korean_response(self, w5h1: W5H1Response, response_type: str = 'default') -> str:
        """한국어 응답 템플릿 적용"""
        
        templates = {
            'alert': """🚨 알림 발생
━━━━━━━━━━━━━━━━━━━━
📍 무엇: {what}
⚠️ 이유: {why}  
⏰ 시간: {when}
📌 위치: {where}
👤 담당: {who}
🔧 조치: {how}
━━━━━━━━━━━━━━━━━━━━""",
            
            'maintenance': """🔧 정비 안내
━━━━━━━━━━━━━━━━━━━━
📋 작업: {what}
💡 목적: {why}
📅 일정: {when}
🏭 구역: {where}
👷 담당: {who}
📝 절차: {how}
━━━━━━━━━━━━━━━━━━━━""",
            
            'analysis': """📊 분석 결과
━━━━━━━━━━━━━━━━━━━━
📈 내용: {what}
🔍 원인: {why}
📅 기간: {when}
🎯 대상: {where}
👨‍💻 분석자: {who}
📋 방법: {how}
━━━━━━━━━━━━━━━━━━━━""",
            
            'status': """✅ 상태 보고
━━━━━━━━━━━━━━━━━━━━
📊 현황: {what}
📌 사유: {why}
🕐 시점: {when}
📍 위치: {where}
👥 확인자: {who}
📋 세부사항: {how}
━━━━━━━━━━━━━━━━━━━━""",
            
            'default': """📋 정보 안내
━━━━━━━━━━━━━━━━━━━━
• 무엇: {what}
• 이유: {why}
• 시간: {when}
• 위치: {where}
• 담당: {who}
• 방법: {how}
━━━━━━━━━━━━━━━━━━━━"""
        }
        
        # 템플릿 선택
        template = templates.get(response_type, templates['default'])
        
        # 템플릿 채우기
        formatted = template.format(
            what=w5h1.what or "정보 없음",
            why=w5h1.why or "정보 없음",
            when=w5h1.when or "정보 없음",
            where=w5h1.where or "정보 없음",
            who=w5h1.who or "정보 없음",
            how=w5h1.how or "정보 없음"
        )
        
        # 신뢰도 정보 추가
        if w5h1.confidence < 1.0:
            formatted += f"\n\n신뢰도: {w5h1.confidence:.1%}"
        
        # 출처 정보 추가
        if w5h1.sources:
            formatted += f"\n출처: {', '.join(w5h1.sources)}"
        
        return formatted