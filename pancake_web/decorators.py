"""参数绑定与返回值解析 — Spring MVC 风格"""

import inspect
import json
import logging
from dataclasses import asdict, is_dataclass

from aiohttp import web

logger = logging.getLogger(__name__)


# ── 参数绑定标记类 ──────────────────────────────────


class _PathVariable:
    """路径变量标记"""
    def __init__(self, name=None):
        self.name = name


class _RequestParam:
    """查询参数标记"""
    def __init__(self, name=None, default=None):
        self.name = name
        self.default = default


class _RequestBody:
    """请求体标记"""
    def __init__(self):
        pass


def path_variable(name=None):
    """path_variable() — 绑定路径变量 /users/{id}"""
    return _PathVariable(name)


def request_param(name=None, default=None):
    """request_param() — 绑定查询参数 ?keyword=xxx"""
    return _RequestParam(name, default)


def request_body():
    """request_body() — 绑定 JSON 请求体"""
    return _RequestBody()


# ── 路由方法标记 ──────────────────────────────────────


def _mark_route(method: str, path: str):
    """标记方法为路由处理器"""
    def decorator(func):
        func._route_method = method
        func._route_path = path
        return func
    return decorator


def get(path: str):
    """@get — GET 路由"""
    return _mark_route("GET", path)


def post(path: str):
    """@post — POST 路由"""
    return _mark_route("POST", path)


def put(path: str):
    """@put — PUT 路由"""
    return _mark_route("PUT", path)


def delete(path: str):
    """@delete — DELETE 路由"""
    return _mark_route("DELETE", path)


# ── 参数解析 ──────────────────────────────────────────


def _convert(value, target_type):
    """类型转换: str → int/float/bool/str"""
    if value is None:
        return None
    if target_type is inspect.Parameter.empty or target_type is str:
        return value
    if target_type is bool:
        return str(value).lower() in ("true", "1", "yes")
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return value


async def resolve_handler_args(request: web.Request, handler) -> dict:
    """按 Spring 风格解析 handler 参数

    解析优先级:
    1. 形参名为 request → 注入 aiohttp Request
    2. 默认值为 path_variable() → 从 URL 路径提取
    3. 默认值为 request_param() → 从 query string 提取
    4. 默认值为 request_body() → 从 JSON body 提取
    5. 无标记的其他参数 → 跳过（由 self 等自动处理）
    """
    sig = inspect.signature(handler)
    kwargs = {}

    for pname, param in sig.parameters.items():
        if pname == "self":
            continue

        # request 自动注入
        if pname == "request":
            kwargs["request"] = request
            continue

        default = param.default

        # 路径变量
        if isinstance(default, _PathVariable):
            key = default.name or pname
            raw = request.match_info.get(key)
            kwargs[pname] = _convert(raw, param.annotation)
            continue

        # 查询参数
        if isinstance(default, _RequestParam):
            key = default.name or pname
            raw = request.query.get(key, default.default)
            kwargs[pname] = _convert(raw, param.annotation)
            continue

        # 请求体
        if isinstance(default, _RequestBody):
            try:
                body = await request.json()
            except (json.JSONDecodeError, Exception):
                body = {}
            ann = param.annotation
            if ann and ann is not inspect.Parameter.empty and is_dataclass(ann):
                # Struct/dataclass 解析
                try:
                    kwargs[pname] = ann(**body)
                except TypeError as e:
                    logger.warning(f"Struct 解析失败: {e}")
                    kwargs[pname] = body
            else:
                kwargs[pname] = body
            continue

    return kwargs


# ── 返回值解析 ──────────────────────────────────────────


def _convert_serializable(obj):
    """递归转换 dataclass 对象为 dict（用于 JSON 序列化）"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, list):
        return [_convert_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _convert_serializable(v) for k, v in obj.items()}
    return obj


async def resolve_response(result, _handler=None, request=None) -> web.Response:
    """自动将 handler 返回值转为 web.Response

    转换规则:
    - None → 204
    - web.Response → 原样返回
    - (data, status) → JsonResponse(data, status)
    - dataclass/Struct → JsonResponse(asdict(data))
    - dict/list → JsonResponse
    - str → HtmlResponse
    - int/float/bool → JsonResponse
    """
    from pancake_web.response import JsonResponse, HtmlResponse

    if result is None:
        return web.Response(status=204)

    if isinstance(result, web.Response):
        return result

    # 元组: (data, status) 或 (data, status, headers)
    if isinstance(result, tuple):
        data = result[0]
        status = result[1] if len(result) > 1 else 200
        headers = result[2] if len(result) > 2 else None
        resp = await resolve_response(data, _handler, request)
        new_resp = web.Response(
            body=resp.body,
            status=status,
            content_type=resp.content_type,
        )
        if headers:
            new_resp.headers.update(headers)
        return new_resp

    # dataclass/Struct
    if is_dataclass(result) and not isinstance(result, type):
        return JsonResponse(asdict(result))

    # dict/list（递归转换其中的 dataclass 对象）
    if isinstance(result, (dict, list)):
        return JsonResponse(_convert_serializable(result))

    # str
    if isinstance(result, str):
        return HtmlResponse(result)

    # int/float/bool/其他
    return JsonResponse(result)
