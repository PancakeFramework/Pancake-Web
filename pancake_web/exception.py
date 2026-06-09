"""异常处理 — @exception_handler 装饰器"""

import logging
from aiohttp import web

logger = logging.getLogger(__name__)

_exception_handlers: dict[type, callable] = {}


def exception_handler(exc_class: type):
    """@exception_handler — 注册全局异常处理器

    Usage:
        @exception_handler(ValueError)
        async def handle_value_error(request, exc):
            return JsonResponse({"error": str(exc)}, status=400)
    """
    def decorator(func):
        _exception_handlers[exc_class] = func
        return func
    return decorator


def get_exception_handlers() -> dict[type, callable]:
    """获取所有注册的异常处理器"""
    return dict(_exception_handlers)


def create_error_middleware():
    """创建 aiohttp 错误处理中间件"""

    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception as exc:
            for exc_class, handler_func in _exception_handlers.items():
                if isinstance(exc, exc_class):
                    try:
                        return await handler_func(request, exc)
                    except Exception as e:
                        logger.error(f"异常处理器失败: {e}")
                        break
            logger.error(f"未处理的异常: {exc}", exc_info=True)
            return web.json_response(
                {"error": str(exc)},
                status=500,
            )

    return error_middleware


def clear_exception_handlers():
    """清空异常处理器（用于测试）"""
    _exception_handlers.clear()
