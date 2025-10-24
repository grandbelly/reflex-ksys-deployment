import reflex as rx
from reflex.constants import LogLevel

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
    frontend_port=14000,
    backend_port=14001,
    backend_host="0.0.0.0",
    backend_transports=rx.constants.Transports.WEBSOCKET_ONLY,
    api_url="https://ksys.idna.ai.kr",
    cors_allowed_origins=[        
        "http://localhost:14000",
        "http://localhost:14001",
        "https://ksys.idna.ai.kr",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
        "*"
    ],
)
