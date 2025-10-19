"""
보안 설정 관리 모듈
TASK_003: SECURITY_ROTATE_API_KEY
"""

import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet


class SecureConfig:
    """보안 설정 관리 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        초기화
        
        Args:
            config_path: 암호화된 설정 파일 경로
        """
        self.config_path = config_path or os.path.join(
            Path.home(), '.ksys', 'secure_config.enc'
        )
        self.key_path = os.path.join(Path.home(), '.ksys', '.key')
        self._ensure_directories()
        self.cipher = self._get_or_create_cipher()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
    
    def _get_or_create_cipher(self) -> Fernet:
        """암호화 키 가져오기 또는 생성"""
        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as f:
                key = f.read()
        else:
            # 새 키 생성
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)
            # 키 파일 권한 설정 (Windows에서는 제한적)
            if hasattr(os, 'chmod'):
                os.chmod(self.key_path, 0o600)
        
        return Fernet(key)
    
    def encrypt_value(self, value: str) -> str:
        """값 암호화"""
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """값 복호화"""
        return self.cipher.decrypt(encrypted_value.encode()).decode()
    
    def save_config(self, config: Dict[str, Any]):
        """설정 저장 (암호화)"""
        # 민감한 키들 암호화
        sensitive_keys = ['OPENAI_API_KEY', 'INFLUX_TOKEN', 'TS_DSN']
        
        encrypted_config = {}
        for key, value in config.items():
            if key in sensitive_keys and value:
                encrypted_config[key] = {
                    'encrypted': True,
                    'value': self.encrypt_value(str(value))
                }
            else:
                encrypted_config[key] = {
                    'encrypted': False,
                    'value': value
                }
        
        # JSON으로 저장
        with open(self.config_path, 'w') as f:
            json.dump(encrypted_config, f, indent=2)
    
    def load_config(self) -> Dict[str, Any]:
        """설정 로드 (복호화)"""
        if not os.path.exists(self.config_path):
            return {}
        
        with open(self.config_path, 'r') as f:
            encrypted_config = json.load(f)
        
        config = {}
        for key, item in encrypted_config.items():
            if item.get('encrypted'):
                try:
                    config[key] = self.decrypt_value(item['value'])
                except Exception as e:
                    print(f"복호화 실패 ({key}): {e}")
                    config[key] = None
            else:
                config[key] = item['value']
        
        return config
    
    def get_api_key(self, key_name: str, fallback_env: str = None) -> Optional[str]:
        """
        API 키 안전하게 가져오기
        
        Args:
            key_name: 키 이름 (예: 'OPENAI_API_KEY')
            fallback_env: 환경변수 fallback 이름
            
        Returns:
            API 키 또는 None
        """
        # 1. 암호화된 설정에서 시도
        config = self.load_config()
        if key_name in config and config[key_name]:
            return config[key_name]
        
        # 2. 환경변수에서 시도
        env_key = fallback_env or key_name
        env_value = os.getenv(env_key)
        if env_value:
            # OpenAI API 키 형태 검증 (sk-로 시작하거나 sk-proj-로 시작)
            if env_value.startswith(('sk-', 'sk-proj-')):
                return env_value
            elif len(env_value) < 10:  # 너무 짧으면 마스킹된 것으로 간주
                return None

        return env_value
    
    def rotate_api_key(self, key_name: str, new_value: str):
        """API 키 교체"""
        config = self.load_config()
        config[key_name] = new_value
        self.save_config(config)
        print(f"[OK] {key_name} key saved securely.")
    
    def mask_api_key(self, api_key: str) -> str:
        """API 키 마스킹"""
        if not api_key:
            return "NOT_SET"
        
        if len(api_key) > 8:
            return f"{api_key[:4]}...{api_key[-4:]}"
        else:
            return "***"


class APIKeyManager:
    """API 키 관리자"""
    
    def __init__(self):
        self.secure_config = SecureConfig()
        self._cached_keys = {}
    
    def get_openai_key(self) -> Optional[str]:
        """OpenAI API 키 가져오기"""
        if 'openai' not in self._cached_keys:
            key = self.secure_config.get_api_key('OPENAI_API_KEY')
            if key:
                self._cached_keys['openai'] = key
        
        return self._cached_keys.get('openai')
    
    def get_influx_token(self) -> Optional[str]:
        """InfluxDB 토큰 가져오기"""
        if 'influx' not in self._cached_keys:
            key = self.secure_config.get_api_key('INFLUX_TOKEN')
            if key:
                self._cached_keys['influx'] = key
        
        return self._cached_keys.get('influx')
    
    def validate_keys(self) -> Dict[str, bool]:
        """모든 키 유효성 검사"""
        results = {}
        
        # OpenAI 키 검사
        openai_key = self.get_openai_key()
        results['openai'] = bool(openai_key and (openai_key.startswith('sk-') or openai_key.startswith('sk-proj-')))
        
        # Influx 토큰 검사
        influx_token = self.get_influx_token()
        results['influx'] = bool(influx_token and len(influx_token) > 20)
        
        return results
    
    def get_status_report(self) -> str:
        """상태 보고서 생성"""
        validation = self.validate_keys()
        
        report = "API Key Status\n"
        report += "=" * 40 + "\n"
        
        openai_key = self.get_openai_key()
        influx_token = self.get_influx_token()
        
        report += f"OpenAI API Key: {self.secure_config.mask_api_key(openai_key)}"
        report += f" {'[OK]' if validation['openai'] else '[FAIL]'}\n"
        
        report += f"Influx Token: {self.secure_config.mask_api_key(influx_token)}"
        report += f" {'[OK]' if validation['influx'] else '[FAIL]'}\n"
        
        return report


# 싱글톤 인스턴스
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """API 키 관리자 싱글톤 인스턴스 가져오기"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager