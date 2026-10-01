from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """監査ログ用にクライアントIPを取得"""
    return request.client.host if request.client else None
