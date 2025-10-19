"""Model Recommendation Logic - 최적 모델 추천 시스템"""

from typing import Dict, List, Any


class ModelRecommender:
    """모델 추천 로직"""

    @staticmethod
    def get_best_for_accuracy(models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """정확도 우선 - Validation MAE가 가장 낮은 모델"""
        if not models:
            return {}

        valid_models = [m for m in models if m.get('validation_mae') is not None]
        if not valid_models:
            return {}

        return min(valid_models, key=lambda m: m['validation_mae'])

    @staticmethod
    def get_best_for_speed(models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """속도 우선 - Training Duration이 가장 짧은 모델"""
        if not models:
            return {}

        valid_models = [m for m in models if m.get('training_duration') is not None]
        if not valid_models:
            return {}

        return min(valid_models, key=lambda m: m['training_duration'])

    @staticmethod
    def get_balanced(models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """균형 - 정확도와 속도의 균형점"""
        if not models:
            return {}

        valid_models = [
            m for m in models
            if m.get('validation_mae') is not None
            and m.get('training_duration') is not None
        ]

        if not valid_models:
            return {}

        # Normalize scores (0-1 scale)
        mae_values = [m['validation_mae'] for m in valid_models]
        duration_values = [m['training_duration'] for m in valid_models]

        min_mae, max_mae = min(mae_values), max(mae_values)
        min_dur, max_dur = min(duration_values), max(duration_values)

        # Calculate normalized scores
        for model in valid_models:
            # Lower MAE is better (normalize and invert)
            mae_score = 1 - (
                (model['validation_mae'] - min_mae) / (max_mae - min_mae)
                if max_mae != min_mae
                else 1.0
            )

            # Lower duration is better (normalize and invert)
            speed_score = 1 - (
                (model['training_duration'] - min_dur) / (max_dur - min_dur)
                if max_dur != min_dur
                else 1.0
            )

            # Balanced score (equal weight)
            model['_balance_score'] = (mae_score + speed_score) / 2

        return max(valid_models, key=lambda m: m['_balance_score'])

    @staticmethod
    def get_insights(models: List[Dict[str, Any]]) -> Dict[str, str]:
        """각 모델에 대한 인사이트 생성"""
        insights = {}

        for model in models:
            model_id = model.get('model_id')
            model_type = model.get('model_type', 'Unknown')
            val_mae = model.get('validation_mae')
            duration = model.get('training_duration')

            # 모델별 특징
            if model_type == 'ARIMA':
                insight = "빠른 예측 속도, 선형 패턴에 적합"
            elif model_type == 'Prophet':
                insight = "계절성 패턴 감지, 속도와 정확도 균형"
            elif model_type == 'XGBoost':
                insight = "높은 정확도, 비선형 패턴 학습 가능"
            else:
                insight = "일반 모델"

            # 성능 추가 정보
            if val_mae and duration:
                if val_mae < 2.0:
                    insight += " (매우 정확)"
                elif val_mae < 2.5:
                    insight += " (정확)"
                else:
                    insight += " (보통)"

                if duration < 20:
                    insight += ", 빠름"
                elif duration < 35:
                    insight += ", 중간 속도"
                else:
                    insight += ", 느림"

            insights[model_id] = insight

        return insights
