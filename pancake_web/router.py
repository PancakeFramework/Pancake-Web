"""路由注册表 — @controller 装饰器 + 路由管理"""

import inspect
import logging

from aiohttp import web

logger = logging.getLogger(__name__)

# 类级: {ControllerClass: prefix}
_controller_registry: dict[type, str] = {}

# 方法级: {(method, full_path): (controller_cls, handler_name)}
_route_registry: dict[tuple[str, str], tuple] = {}


def controller(prefix: str = ""):
    """@controller — 标记类为 Web 控制器，自动注册为 Dough 子类

    Controller 实例由 DoughFactory 管理（IoC），支持 @inject 注入依赖。

    Usage:
        @controller("/api/users")
        class UserController:
            user_service: UserService = inject()

            @get("/")
            async def list_users(self, request):
                return self.user_service.find_all()
    """
    def decorator(cls):
        from pancake.dough import Dough, Scope
        from pancake.decorators.convert import _convert_class

        # 转为 Dough 子类（IoC 容器管理）
        cls = _convert_class(cls, Dough, dough_type="controller")
        cls._scope = Scope.SINGLETON

        _controller_registry[cls] = prefix

        # 扫描类方法上的 @get/@post 等装饰器标记
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(method, "_route_method"):
                route_path = method._route_path
                if route_path == "/":
                    full_path = prefix if prefix else "/"
                else:
                    full_path = prefix.rstrip("/") + route_path
                if not full_path:
                    full_path = "/"
                _route_registry[(method._route_method, full_path)] = (cls, name)
                logger.debug(f"注册路由: {method._route_method} {full_path} -> {cls.__name__}.{name}")

        return cls
    return decorator


def get_controller_registry() -> dict[type, str]:
    """获取控制器注册表"""
    return dict(_controller_registry)


def get_route_registry() -> dict[tuple[str, str], tuple]:
    """获取路由注册表"""
    return dict(_route_registry)


def register_routes(app: web.Application):
    """将注册表中的路由注册到 aiohttp app

    从 DoughFactory 获取 Controller 实例（IoC），
    自动解析参数并转换返回值。
    """
    from pancake.factory.dough_factory import DoughFactory
    from pancake_web.decorators import resolve_handler_args, resolve_response

    for (method, path), (cls, handler_name) in _route_registry.items():
        # 从 IoC 容器获取 Controller 实例
        try:
            instance = DoughFactory.get().resolve(cls.__name__)
        except (ValueError, Exception):
            logger.warning(f"Controller {cls.__name__} 未在 DoughFactory 中注册，跳过路由 {method} {path}")
            continue

        handler = getattr(instance, handler_name)

        async def aiohttp_handler(request, _handler=handler, _name=f"{cls.__name__}.{handler_name}"):
            try:
                # 1. 解析参数（Spring 风格）
                kwargs = await resolve_handler_args(request, _handler)
                # 2. 调用 handler
                result = await _handler(**kwargs)
                # 3. 自动转为 Response
                return await resolve_response(result)
            except web.HTTPException:
                raise
            except Exception as e:
                logger.error(f"Handler {_name} 异常: {e}", exc_info=True)
                raise

        app.router.add_route(method, path, aiohttp_handler)
        logger.info(f"路由已注册: {method} {path} -> {cls.__name__}.{handler_name}")


def clear_registries():
    """清空所有注册表（用于测试）"""
    _controller_registry.clear()
    _route_registry.clear()
