import reflex as rx
from reflex.constants import LogLevel

config = rx.Config(
    app_name="ksys_app",
    loglevel=LogLevel.DEBUG,
    show_built_with_reflex=False,
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
)
