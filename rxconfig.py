import reflex as rx
from reflex.constants import LogLevel
import os

# 환경 감지: 프로덕션(RPI 배포) vs 개발(로컬)
APP_ENV = os.getenv("APP_ENV", "development")

# API URL 설정
if APP_ENV == "production":
    # 프로덕션: Cloudflare 도메인 사용
    api_url = "https://ksys.idna.ai.kr"
else:
    # 개발: localhost 사용
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
        "https://ksys.idna.ai.kr",
        "*"
    ],
)
