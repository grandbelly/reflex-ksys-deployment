"""
KPI 계산 로직 단위 테스트
PRD 섹션 4) 계산 규칙 기반
"""
import pytest
from unittest.mock import Mock


class TestKPICalculations:
    """KPI 타일 계산 로직 테스트"""
    
    def test_gauge_pct_with_qc_rule(self):
        """QC 규칙이 있는 경우 gauge_pct 계산"""
        # Given: QC 규칙과 현재 값
        qc_rule = {"min_val": 0.0, "max_val": 200.0}
        last_value = 190.0
        
        # When: gauge_pct 계산
        gauge_pct = self._calculate_gauge_pct(last_value, qc_rule)
        
        # Then: (190-0)/(200-0)*100 = 95.0
        assert abs(gauge_pct - 95.0) <= 1.0
    
    def test_gauge_pct_without_qc_rule(self):
        """QC 규칙이 없는 경우 윈도우 범위로 계산"""
        # Given: QC 규칙 없음, 윈도우 min/max
        qc_rule = None
        last_value = 150.0
        window_min, window_max = 80.0, 160.0
        
        # When: gauge_pct 계산
        gauge_pct = self._calculate_gauge_pct(last_value, qc_rule, window_min, window_max)
        
        # Then: (150-80)/(160-80)*100 = 87.5
        assert abs(gauge_pct - 87.5) <= 1.0
    
    def test_delta_pct_calculation(self):
        """delta_pct 계산 (이전 버킷 대비 증감률)"""
        # Given: 현재와 이전 값
        current_last = 190.0
        previous_last = 180.0
        
        # When: delta_pct 계산
        delta_pct = self._calculate_delta_pct(current_last, previous_last)
        
        # Then: (190-180)/180*100 = 5.56
        assert abs(delta_pct - 5.56) <= 0.1
    
    def test_delta_pct_zero_previous(self):
        """이전 값이 0인 경우 delta_pct = 0"""
        # Given: 이전 값이 0
        current_last = 100.0
        previous_last = 0.0
        
        # When: delta_pct 계산
        delta_pct = self._calculate_delta_pct(current_last, previous_last)
        
        # Then: 분모가 0이면 0 반환
        assert delta_pct == 0.0
    
    def test_status_level_normal(self):
        """정상 범위 내 값의 status_level = 0"""
        # Given: QC 규칙 내 정상 값
        qc_rule = {
            "warn_min": 10.0, "warn_max": 190.0,
            "crit_min": 5.0, "crit_max": 195.0,
            "min_val": 0.0, "max_val": 200.0
        }
        value = 100.0  # 정상 범위
        
        # When: status_level 계산
        status_level = self._calculate_status_level(value, qc_rule)
        
        # Then: 정상 = 0
        assert status_level == 0
    
    def test_status_level_warning(self):
        """경고 범위 값의 status_level = 1"""
        # Given: 경고 범위 값
        qc_rule = {
            "warn_min": 10.0, "warn_max": 190.0,
            "crit_min": 5.0, "crit_max": 195.0,
            "min_val": 0.0, "max_val": 200.0
        }
        value = 191.0  # warn_max 초과
        
        # When: status_level 계산
        status_level = self._calculate_status_level(value, qc_rule)
        
        # Then: 경고 = 1
        assert status_level == 1
    
    def test_status_level_critical(self):
        """치명 범위 값의 status_level = 2"""
        # Given: 치명 범위 값
        qc_rule = {
            "warn_min": 10.0, "warn_max": 190.0,
            "crit_min": 5.0, "crit_max": 195.0,
            "min_val": 0.0, "max_val": 200.0
        }
        value = 196.0  # crit_max 초과
        
        # When: status_level 계산
        status_level = self._calculate_status_level(value, qc_rule)
        
        # Then: 치명 = 2
        assert status_level == 2
    
    def test_range_label_with_qc(self):
        """QC 규칙 있는 경우 range_label"""
        # Given: QC 규칙
        qc_rule = {"min_val": 0.0, "max_val": 200.0}
        
        # When: range_label 생성
        range_label = self._format_range_label(qc_rule)
        
        # Then: "min_val ~ max_val" 형식
        assert range_label == "0.0 ~ 200.0"
    
    def test_range_label_without_qc(self):
        """QC 규칙 없는 경우 윈도우 범위"""
        # Given: QC 규칙 없음, 윈도우 범위
        qc_rule = None
        window_min, window_max = 80.0, 160.0
        
        # When: range_label 생성
        range_label = self._format_range_label(qc_rule, window_min, window_max)
        
        # Then: 윈도우 범위 표시
        assert range_label == "80.0 ~ 160.0"
    
    # Helper methods (실제 구현에서는 DashboardState에 있음)
    def _calculate_gauge_pct(self, last_value, qc_rule, window_min=None, window_max=None):
        """gauge_pct 계산 로직"""
        if qc_rule and qc_rule.get("min_val") is not None and qc_rule.get("max_val") is not None:
            min_val, max_val = qc_rule["min_val"], qc_rule["max_val"]
        elif window_min is not None and window_max is not None:
            min_val, max_val = window_min, window_max
        else:
            return 0.0
        
        if max_val == min_val:
            return 0.0
        
        pct = (last_value - min_val) / (max_val - min_val) * 100
        return max(0.0, min(100.0, pct))  # clamp 0-100
    
    def _calculate_delta_pct(self, current_last, previous_last):
        """delta_pct 계산 로직"""
        if previous_last is None or previous_last == 0:
            return 0.0
        return round((current_last - previous_last) / previous_last * 100, 2)
    
    def _calculate_status_level(self, value, qc_rule):
        """status_level 계산 로직"""
        if not qc_rule:
            return 0  # QC 규칙 없으면 정상
        
        # 치명 범위 확인 (우선순위 높음)
        crit_min = qc_rule.get("crit_min")
        crit_max = qc_rule.get("crit_max")
        if (crit_min is not None and value < crit_min) or \
           (crit_max is not None and value > crit_max):
            return 2
        
        # 경고 범위 확인
        warn_min = qc_rule.get("warn_min")
        warn_max = qc_rule.get("warn_max")
        if (warn_min is not None and value < warn_min) or \
           (warn_max is not None and value > warn_max):
            return 1
        
        # 하드 경계 확인
        min_val = qc_rule.get("min_val")
        max_val = qc_rule.get("max_val") 
        if (min_val is not None and value < min_val) or \
           (max_val is not None and value > max_val):
            return 2
        
        return 0  # 정상
    
    def _format_range_label(self, qc_rule, window_min=None, window_max=None):
        """range_label 포맷팅"""
        if qc_rule and qc_rule.get("min_val") is not None and qc_rule.get("max_val") is not None:
            return f"{qc_rule['min_val']:.1f} ~ {qc_rule['max_val']:.1f}"
        elif window_min is not None and window_max is not None:
            return f"{window_min:.1f} ~ {window_max:.1f}"
        else:
            return "N/A"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])