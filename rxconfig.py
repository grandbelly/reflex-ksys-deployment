import reflex as rx
from reflex.constants import LogLevel
import os

# 배포 환경에 따라 API URL 설정
DOCKER_ENV = os.getenv("DOCKER_ENV", "false").lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development")

# API URL: 백엔드 포트(13001)를 명시적으로 지정
if DOCKER_ENV and APP_ENV == "production":
    # 프로덕션: Cloudflare가 /_event를 13001로 라우팅
    # 하지만 기본 API 호출도 13001로 가야 함
    api_url = "https://ksys.idna.ai.kr"
else:
    # 로컬 개발
    api_url = "http://localhost:13001"

config = rx.Config(
    app_name="ksys_app",
    loglevel=LogLevel.DEBUG,
    frontend_packages=[],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV3Plugin(
            config={
                "theme": {
                    "extend": {
                        "colors": {
                            "slate": {
                                "850": "#1a202e",
                            },
                            "status": {
                                "normal": "#10b981",
                                "warning": "#f59e0b",
                                "critical": "#ef4444",
                            }
                        },
                        "fontFamily": {
                            "sans": ["Inter", "system-ui", "sans-serif"],
                        }
                    }
                }
            }
        ),
    ],
    frontend_port=13000,
    backend_port=13001,
    backend_host="0.0.0.0",
    api_url=api_url,
    cors_allowed_origins=[
        "http://localhost:13000",
        "http://localhost:13001",
        "http://localhost:14000",
        "http://localhost:14001",
        "https://ksys.idna.ai.kr",
        "*"
    ],
)
