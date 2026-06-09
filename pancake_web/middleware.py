"""中间件 — @middleware 装饰器"""

import inspect
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

_middleware_registry: list[tuple[int, callable]] = []


def middleware(order: int = 0):
    """@middleware — 注册中间件，order 越小越先执行

    支持类和函数两种形式:

    类形式:
        @middleware(order=0)
        class CorsMiddleware:
            async def process(self, request, handler):
                response = await handler(request)
                response.headers["Access-Control-Allow-Origin"] = "*"
                return response

    函数形式:
        @middleware(order=1)
        async def logging_middleware(request, handler):
            logger.info(f"{request.method} {request.path}")
            return await handler(request)
    """
    def decorator(cls_or_func):
        _middleware_registry.append((order, cls_or_func))
        return cls_or_func
    return decorator


def get_middlewares() -> list[tuple[int, callable]]:
    """获取所有注册的中间件（按 order 排序）"""
    return sorted(_middleware_registry, key=lambda x: x[0])


def build_aiohttp_middlewares() -> list:
    """将注册的中间件转为 aiohttp middleware 列表"""
    aiohttp_middlewares = []

    for order, mw in get_middlewares():
        if inspect.isclass(mw):
            # 类中间件: 实例化并包装为 aiohttp middleware
            instance = mw()

            @web.middleware
            async def class_middleware(request, handler, _inst=instance):
                return await _inst.process(request, handler)

            aiohttp_middlewares.append(class_middleware)
        elif inspect.iscoroutinefunction(mw):
            # 函数中间件: 直接包装
            @web.middleware
            async def func_middleware(request, handler, _fn=mw):
                return await _fn(request, handler)

            aiohttp_middlewares.append(func_middleware)
        else:
            logger.warning(f"不支持的中间件类型: {type(mw)}")

    return aiohttp_middlewares


def clear_middlewares():
    """清空中间件（用于测试）"""
    _middleware_registry.clear()
