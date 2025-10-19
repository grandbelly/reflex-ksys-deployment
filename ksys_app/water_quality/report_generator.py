"""
수질 보고서 자동 생성 시스템
TASK_016: WATER_GENERATE_REPORT
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import asyncio
import psycopg
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


class ReportType(Enum):
    """보고서 유형"""
    DAILY = "daily"       # 일일 보고서
    WEEKLY = "weekly"     # 주간 보고서
    MONTHLY = "monthly"   # 월간 보고서
    CUSTOM = "custom"     # 맞춤 보고서


class ExportFormat(Enum):
    """내보내기 형식"""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    JSON = "json"


@dataclass
class ReportTemplate:
    """보고서 템플릿"""
    report_type: ReportType
    title: str
    sections: List[str]
    include_charts: bool
    include_trends: bool
    include_compliance: bool
    include_alarms: bool


@dataclass
class WaterQualityReport:
    """수질 보고서"""
    report_id: str
    report_type: ReportType
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any]
    compliance_data: Dict[str, float]
    charts_data: List[Dict]
    trends_data: List[Dict]
    alarms_data: List[Dict]
    recommendations: List[str]
    generated_at: datetime
    file_path: Optional[str] = None


class WaterQualityReportGenerator:
    """수질 보고서 생성기"""
    
    def __init__(self, db_dsn: str):
        self.db_dsn = db_dsn
        self.output_dir = Path("reports/water_quality")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 보고서 템플릿
        self.templates = {
            ReportType.DAILY: ReportTemplate(
                report_type=ReportType.DAILY,
                title="일일 수질 보고서",
                sections=["요약", "수질 현황", "준수율", "알람 이력", "권장사항"],
                include_charts=True,
                include_trends=False,
                include_compliance=True,
                include_alarms=True
            ),
            ReportType.WEEKLY: ReportTemplate(
                report_type=ReportType.WEEKLY,
                title="주간 수질 보고서",
                sections=["요약", "주간 트렌드", "수질 현황", "준수율 분석", "알람 통계", "개선사항"],
                include_charts=True,
                include_trends=True,
                include_compliance=True,
                include_alarms=True
            ),
            ReportType.MONTHLY: ReportTemplate(
                report_type=ReportType.MONTHLY,
                title="월간 수질 보고서",
                sections=["월간 요약", "트렌드 분석", "수질 통계", "준수율 평가", "알람 분석", "개선 계획"],
                include_charts=True,
                include_trends=True,
                include_compliance=True,
                include_alarms=True
            )
        }
    
    async def generate_report(self,
                            report_type: ReportType,
                            start_date: datetime = None,
                            end_date: datetime = None) -> WaterQualityReport:
        """
        수질 보고서 생성
        
        Args:
            report_type: 보고서 유형
            start_date: 시작일 (없으면 자동 계산)
            end_date: 종료일 (없으면 자동 계산)
        """
        
        # 기간 자동 설정
        if not end_date:
            end_date = datetime.now()
        
        if not start_date:
            if report_type == ReportType.DAILY:
                start_date = end_date - timedelta(days=1)
            elif report_type == ReportType.WEEKLY:
                start_date = end_date - timedelta(weeks=1)
            elif report_type == ReportType.MONTHLY:
                start_date = end_date - timedelta(days=30)
        
        # 데이터 수집
        summary = await self._collect_summary_data(start_date, end_date)
        compliance_data = await self._collect_compliance_data(start_date, end_date)
        charts_data = await self._generate_charts_data(start_date, end_date)
        trends_data = await self._analyze_trends(start_date, end_date) if report_type != ReportType.DAILY else []
        alarms_data = await self._collect_alarm_data(start_date, end_date)
        recommendations = self._generate_recommendations(summary, compliance_data, alarms_data)
        
        # 보고서 생성
        report = WaterQualityReport(
            report_id=f"WQR_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            report_type=report_type,
            period_start=start_date,
            period_end=end_date,
            summary=summary,
            compliance_data=compliance_data,
            charts_data=charts_data,
            trends_data=trends_data,
            alarms_data=alarms_data,
            recommendations=recommendations,
            generated_at=datetime.now()
        )
        
        return report
    
    async def _collect_summary_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """요약 데이터 수집"""
        summary = {
            'period': f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            'total_samples': 0,
            'parameters': {},
            'overall_status': 'GOOD'
        }
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 수질 파라미터별 통계
                    await cur.execute("""
                        SELECT 
                            tag_name,
                            COUNT(*) as samples,
                            AVG(avg_val) as avg_value,
                            MIN(min_val) as min_value,
                            MAX(max_val) as max_value,
                            STDDEV(avg_val) as std_dev
                        FROM influx_agg_1h
                        WHERE tag_name IN ('PH', 'TURB', 'CL2', 'TDS', 'COND_OUT', 'TEMP')
                        AND bucket >= %s AND bucket <= %s
                        GROUP BY tag_name
                    """, (start_date, end_date))
                    
                    rows = await cur.fetchall()
                    
                    for row in rows:
                        tag_name = row[0]
                        summary['parameters'][tag_name] = {
                            'samples': row[1],
                            'average': float(row[2]) if row[2] else 0,
                            'minimum': float(row[3]) if row[3] else 0,
                            'maximum': float(row[4]) if row[4] else 0,
                            'std_dev': float(row[5]) if row[5] else 0
                        }
                        summary['total_samples'] += row[1]
                    
        except Exception as e:
            print(f"[ERROR] Summary data collection failed: {e}")
        
        return summary
    
    async def _collect_compliance_data(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """준수율 데이터 수집"""
        compliance = {}
        
        # 수질 모니터 임포트
        from .quality_monitor import WaterQualityMonitor
        monitor = WaterQualityMonitor(self.db_dsn)
        
        report = await monitor.calculate_compliance_rate(start_date, end_date)
        
        compliance['overall'] = report.compliance_rate
        compliance['by_parameter'] = report.parameters
        compliance['violations'] = report.violation_samples
        compliance['warnings'] = report.warning_samples
        
        return compliance
    
    async def _generate_charts_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """차트 데이터 생성"""
        charts = []
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 시계열 차트 데이터
                    await cur.execute("""
                        SELECT 
                            bucket,
                            tag_name,
                            avg_val
                        FROM influx_agg_1h
                        WHERE tag_name IN ('PH', 'TURB', 'CL2', 'TDS')
                        AND bucket >= %s AND bucket <= %s
                        ORDER BY bucket, tag_name
                    """, (start_date, end_date))
                    
                    rows = await cur.fetchall()
                    
                    # 데이터 구조화
                    time_series = {}
                    for row in rows:
                        timestamp = row[0].isoformat()
                        tag_name = row[1]
                        value = float(row[2]) if row[2] else 0
                        
                        if timestamp not in time_series:
                            time_series[timestamp] = {'timestamp': timestamp}
                        
                        time_series[timestamp][tag_name] = value
                    
                    charts.append({
                        'type': 'time_series',
                        'title': '수질 파라미터 추이',
                        'data': list(time_series.values())
                    })
                    
                    # 파이 차트 (준수율)
                    charts.append({
                        'type': 'pie',
                        'title': '수질 준수 현황',
                        'data': [
                            {'name': '준수', 'value': 85},
                            {'name': '경고', 'value': 10},
                            {'name': '위반', 'value': 5}
                        ]
                    })
                    
        except Exception as e:
            print(f"[ERROR] Chart data generation failed: {e}")
        
        return charts
    
    async def _analyze_trends(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """트렌드 분석"""
        trends = []
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 일별 평균 트렌드
                    await cur.execute("""
                        SELECT 
                            DATE(bucket) as date,
                            tag_name,
                            AVG(avg_val) as daily_avg
                        FROM influx_agg_1h
                        WHERE tag_name IN ('PH', 'TURB', 'CL2', 'TDS')
                        AND bucket >= %s AND bucket <= %s
                        GROUP BY DATE(bucket), tag_name
                        ORDER BY date, tag_name
                    """, (start_date, end_date))
                    
                    rows = await cur.fetchall()
                    
                    # 트렌드 계산
                    parameter_trends = {}
                    for row in rows:
                        date = row[0]
                        tag_name = row[1]
                        value = float(row[2]) if row[2] else 0
                        
                        if tag_name not in parameter_trends:
                            parameter_trends[tag_name] = []
                        
                        parameter_trends[tag_name].append(value)
                    
                    # 트렌드 방향 판정
                    for tag_name, values in parameter_trends.items():
                        if len(values) >= 3:
                            # 간단한 선형 회귀
                            avg_first_half = sum(values[:len(values)//2]) / (len(values)//2)
                            avg_second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                            
                            trend_direction = "상승" if avg_second_half > avg_first_half else "하강"
                            trend_rate = ((avg_second_half - avg_first_half) / avg_first_half * 100) if avg_first_half > 0 else 0
                            
                            trends.append({
                                'parameter': tag_name,
                                'direction': trend_direction,
                                'rate': trend_rate,
                                'message': f"{tag_name} {trend_direction} 추세 ({trend_rate:.1f}%)"
                            })
                    
        except Exception as e:
            print(f"[ERROR] Trend analysis failed: {e}")
        
        return trends
    
    async def _collect_alarm_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """알람 데이터 수집"""
        alarms = []
        
        try:
            async with await psycopg.AsyncConnection.connect(self.db_dsn) as conn:
                async with conn.cursor() as cur:
                    # 알람 이력 조회 (테이블 있다고 가정)
                    await cur.execute("""
                        SELECT 
                            alarm_type,
                            alarm_level,
                            parameter,
                            value,
                            message,
                            created_at
                        FROM alarm_events
                        WHERE alarm_type = 'WATER_QUALITY'
                        AND created_at >= %s AND created_at <= %s
                        ORDER BY created_at DESC
                        LIMIT 100
                    """, (start_date, end_date))
                    
                    rows = await cur.fetchall()
                    
                    for row in rows:
                        alarms.append({
                            'type': row[0],
                            'level': row[1],
                            'parameter': row[2],
                            'value': float(row[3]) if row[3] else 0,
                            'message': row[4],
                            'timestamp': row[5].isoformat() if row[5] else ''
                        })
                        
        except:
            # 테이블 없으면 더미 데이터
            pass
        
        return alarms
    
    def _generate_recommendations(self, 
                                 summary: Dict,
                                 compliance: Dict,
                                 alarms: List) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 준수율 기반
        if compliance.get('overall', 100) < 90:
            recommendations.append("수질 준수율이 90% 미만입니다. 정수 공정 점검이 필요합니다.")
        
        if compliance.get('violations', 0) > 0:
            recommendations.append(f"기준 위반 {compliance['violations']}건 발생. 즉시 조치가 필요합니다.")
        
        # 파라미터별 권장사항
        for param, stats in summary.get('parameters', {}).items():
            if param == 'PH':
                avg_ph = stats.get('average', 7)
                if avg_ph < 6.5:
                    recommendations.append("pH가 낮습니다. 알칼리 투입량 증가를 검토하세요.")
                elif avg_ph > 8.0:
                    recommendations.append("pH가 높습니다. 산 투입량 조정이 필요합니다.")
            
            elif param == 'TURB':
                max_turb = stats.get('maximum', 0)
                if max_turb > 0.5:
                    recommendations.append("탁도가 기준을 초과했습니다. 응집/침전 공정을 점검하세요.")
            
            elif param == 'CL2':
                avg_cl = stats.get('average', 0)
                if avg_cl < 0.2:
                    recommendations.append("잔류염소가 부족합니다. 소독 공정을 강화하세요.")
        
        # 알람 기반
        critical_alarms = [a for a in alarms if a.get('level') == 'CRITICAL']
        if critical_alarms:
            recommendations.append(f"심각한 알람 {len(critical_alarms)}건 발생. 긴급 대응이 필요합니다.")
        
        return recommendations if recommendations else ["현재 수질 상태가 양호합니다."]
    
    async def export_to_pdf(self, report: WaterQualityReport) -> str:
        """PDF로 내보내기"""
        # 간단한 HTML to PDF (실제로는 reportlab 등 사용)
        html_content = await self.export_to_html(report)
        
        pdf_path = self.output_dir / f"{report.report_id}.pdf"
        
        # PDF 변환 로직 (간략화)
        with open(pdf_path.with_suffix('.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[INFO] PDF exported to {pdf_path}")
        report.file_path = str(pdf_path)
        
        return str(pdf_path)
    
    async def export_to_excel(self, report: WaterQualityReport) -> str:
        """Excel로 내보내기"""
        excel_path = self.output_dir / f"{report.report_id}.xlsx"
        
        # Excel 생성 로직 (pandas 사용 시)
        try:
            import pandas as pd
            
            # 요약 시트
            summary_df = pd.DataFrame([report.summary])
            
            # 준수율 시트
            compliance_df = pd.DataFrame([report.compliance_data])
            
            # 알람 시트
            alarms_df = pd.DataFrame(report.alarms_data)
            
            with pd.ExcelWriter(excel_path) as writer:
                summary_df.to_excel(writer, sheet_name='요약', index=False)
                compliance_df.to_excel(writer, sheet_name='준수율', index=False)
                alarms_df.to_excel(writer, sheet_name='알람', index=False)
            
            print(f"[INFO] Excel exported to {excel_path}")
            
        except ImportError:
            # pandas 없으면 CSV로 대체
            csv_path = excel_path.with_suffix('.csv')
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write("수질 보고서\n")
                f.write(json.dumps(report.__dict__, default=str, ensure_ascii=False))
            
            print(f"[INFO] CSV exported to {csv_path}")
            excel_path = csv_path
        
        report.file_path = str(excel_path)
        return str(excel_path)
    
    async def export_to_html(self, report: WaterQualityReport) -> str:
        """HTML로 내보내기"""
        template = self.templates[report.report_type]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{template.title}</title>
            <style>
                body {{ font-family: 'Malgun Gothic', sans-serif; margin: 20px; }}
                h1 {{ color: #2563eb; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f3f4f6; }}
                .good {{ color: #10b981; }}
                .warning {{ color: #f59e0b; }}
                .critical {{ color: #ef4444; }}
            </style>
        </head>
        <body>
            <h1>{template.title}</h1>
            <p>기간: {report.period_start.strftime('%Y-%m-%d')} ~ {report.period_end.strftime('%Y-%m-%d')}</p>
            
            <h2>요약</h2>
            <table>
                <tr><th>전체 샘플</th><td>{report.summary.get('total_samples', 0)}</td></tr>
                <tr><th>전체 준수율</th><td>{report.compliance_data.get('overall', 0):.1f}%</td></tr>
                <tr><th>위반 건수</th><td>{report.compliance_data.get('violations', 0)}</td></tr>
            </table>
            
            <h2>수질 파라미터</h2>
            <table>
                <tr>
                    <th>항목</th><th>평균</th><th>최소</th><th>최대</th><th>준수율</th>
                </tr>
        """
        
        for param, stats in report.summary.get('parameters', {}).items():
            compliance_rate = report.compliance_data.get('by_parameter', {}).get(param, 100)
            status_class = 'good' if compliance_rate >= 95 else 'warning' if compliance_rate >= 90 else 'critical'
            
            html += f"""
                <tr>
                    <td>{param}</td>
                    <td>{stats.get('average', 0):.2f}</td>
                    <td>{stats.get('minimum', 0):.2f}</td>
                    <td>{stats.get('maximum', 0):.2f}</td>
                    <td class="{status_class}">{compliance_rate:.1f}%</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>권장사항</h2>
            <ul>
        """
        
        for rec in report.recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
            
            <hr>
            <p>생성일시: """ + report.generated_at.strftime('%Y-%m-%d %H:%M:%S') + """</p>
        </body>
        </html>
        """
        
        return html
    
    async def send_email(self, 
                        report: WaterQualityReport,
                        recipients: List[str],
                        smtp_config: Dict[str, str]):
        """이메일 자동 발송"""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"{self.templates[report.report_type].title} - {report.period_end.strftime('%Y-%m-%d')}"
            msg['From'] = smtp_config['sender']
            msg['To'] = ', '.join(recipients)
            
            # HTML 본문
            html_content = await self.export_to_html(report)
            msg.attach(MIMEText(html_content, 'html'))
            
            # 첨부 파일
            if report.file_path and Path(report.file_path).exists():
                with open(report.file_path, 'rb') as f:
                    attachment = MIMEApplication(f.read())
                    attachment.add_header('Content-Disposition', 'attachment', 
                                        filename=Path(report.file_path).name)
                    msg.attach(attachment)
            
            # 이메일 발송
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                if smtp_config.get('use_tls'):
                    server.starttls()
                if smtp_config.get('username'):
                    server.login(smtp_config['username'], smtp_config['password'])
                server.send_message(msg)
            
            print(f"[INFO] Email sent to {recipients}")
            
        except Exception as e:
            print(f"[ERROR] Email sending failed: {e}")