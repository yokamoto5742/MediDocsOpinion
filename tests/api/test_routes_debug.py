"""ルート確認用デバッグテスト"""
from fastapi.routing import APIRoute

from app.main import app


def test_list_routes():
    """登録されているルートを確認"""
    for route in app.routes:
        if isinstance(route, APIRoute):
            print(f"{route.methods} {route.path}")
            if hasattr(route, "dependencies"):
                print(f"  Dependencies: {route.dependencies}")
