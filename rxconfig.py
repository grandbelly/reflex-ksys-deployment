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
    frontend_port=13000,
    backend_port=13001,
    backend_host="0.0.0.0",
    api_url="http://localhost:13001",
    cors_allowed_origins=["http://localhost:13000", "http://localhost:13001", "*"],
)
