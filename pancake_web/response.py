"""响应类型 — JsonResponse, HtmlResponse"""

import json
from aiohttp import web


class JsonResponse(web.Response):
    """JSON 响应"""

    def __init__(self, data, status=200, **kwargs):
        super().__init__(
            text=json.dumps(data, ensure_ascii=False, default=str),
            content_type="application/json",
            status=status,
            **kwargs,
        )


class HtmlResponse(web.Response):
    """HTML 响应"""

    def __init__(self, body, status=200, **kwargs):
        super().__init__(
            text=body,
            content_type="text/html",
            status=status,
            **kwargs,
        )
