"""Static file server and Single Page Application fallback for FastAPI."""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles


def mount_static_app(app: FastAPI, dist_dir: Path) -> None:
    """Mount compiled frontend static files and configure SPA routing fallback."""
    if not dist_dir.exists():
        @app.get("/")
        def frontend_placeholder():
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head><title>FounderOS LinkedIn Studio</title>
            <style>
              body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
              .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; border: 1px solid #334155; text-align: center; max-width: 500px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
              h1 { color: #38bdf8; margin-top: 0; }
              a { color: #38bdf8; text-decoration: none; font-weight: bold; }
              code { background: #0f172a; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
            </style>
            </head>
            <body>
              <div class="card">
                <h1>FounderOS LinkedIn Studio</h1>
                <p>Backend API is active and ready!</p>
                <p>To view the dashboard, run <code>npm run build</code> in the <code>frontend/</code> directory or run <code>npm run dev</code> for local development.</p>
                <p><a href="/api/docs">View API Documentation &rarr;</a></p>
              </div>
            </body>
            </html>
            """)
        return

    # Assets folder
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA catch-all for React Router
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API routes to be handled by FastAPI
        if full_path.startswith("api/") or full_path == "healthz":
            return None
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")
