"""ルート確認用デバッグテスト"""
from app.main import app


def test_list_routes():
    """登録されているルートを確認"""
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            print(f"{route.methods} {route.path}")
            if hasattr(route, "dependencies"):
                print(f"  Dependencies: {route.dependencies}")
