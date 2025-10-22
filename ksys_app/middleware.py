"""
Custom middleware for handling CORS and MIME types for static assets
Fixes font loading issues in production
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class FontCORSMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add CORS headers for font files and ensure correct MIME types

    Fixes:
    - CORS errors when loading fonts from CDN or different origins
    - Incorrect MIME types for .woff2, .woff, .ttf files
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Get request path
        path = request.url.path

        # Font file extensions
        font_extensions = ['.woff2', '.woff', '.ttf', '.otf', '.eot']

        # Check if this is a font file request
        is_font = any(path.endswith(ext) for ext in font_extensions)

        if is_font:
            logger.debug(f"Font file requested: {path}")

            # Add CORS headers for font files
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = '*'

            # Set correct MIME types for font files
            if path.endswith('.woff2'):
                response.headers['Content-Type'] = 'font/woff2'
            elif path.endswith('.woff'):
                response.headers['Content-Type'] = 'font/woff'
            elif path.endswith('.ttf'):
                response.headers['Content-Type'] = 'font/ttf'
            elif path.endswith('.otf'):
                response.headers['Content-Type'] = 'font/otf'
            elif path.endswith('.eot'):
                response.headers['Content-Type'] = 'application/vnd.ms-fontobject'

            # Add caching headers for performance
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

            logger.debug(f"Font CORS headers added: {response.headers}")

        # Also add CORS for other static assets (CSS, JS)
        if path.endswith('.css') or path.endswith('.js'):
            response.headers['Access-Control-Allow-Origin'] = '*'

        return response


class StaticAssetMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure correct MIME types and caching for all static assets
    """

    MIME_TYPES = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff2': 'font/woff2',
        '.woff': 'font/woff',
        '.ttf': 'font/ttf',
        '.otf': 'font/otf',
        '.eot': 'application/vnd.ms-fontobject',
    }

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        path = request.url.path

        # Set correct MIME type based on file extension
        for ext, mime_type in self.MIME_TYPES.items():
            if path.endswith(ext):
                response.headers['Content-Type'] = mime_type

                # Add CORS for web fonts and static assets
                if ext in ['.woff2', '.woff', '.ttf', '.otf', '.eot', '.css', '.js']:
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'

                # Add caching for static assets
                if ext in ['.woff2', '.woff', '.ttf', '.otf', '.eot', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']:
                    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                elif ext in ['.css', '.js']:
                    response.headers['Cache-Control'] = 'public, max-age=3600'

                logger.debug(f"Static asset served: {path} ({mime_type})")
                break

        return response
