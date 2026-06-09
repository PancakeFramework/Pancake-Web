"""Pancake Web 插件 — Spring MVC 风格 aiohttp Web 服务器"""

import logging
from pancake.ovenware import InitAction

logger = logging.getLogger(__name__)


class Main(InitAction):
    """Web 插件入口

    init_order=50, 在 embed(999) 之前加载。
    提供 aiohttp Web 服务器、路由注册、参数绑定、中间件、异常处理。
    """

    init_order = 50
    build_order = 0

    def __init__(self):
        from pancake.registry import export

        # 路由装饰器
        from pancake_web.router import controller
        export(controller)

        # HTTP 方法装饰器
        from pancake_web.decorators import get, post, put, delete
        export(get)
        export(post)
        export(put)
        export(delete)

        # 参数绑定
        from pancake_web.decorators import path_variable, request_param, request_body
        export(path_variable)
        export(request_param)
        export(request_body)

        # 中间件
        from pancake_web.middleware import middleware
        export(middleware)

        # 异常处理
        from pancake_web.exception import exception_handler
        export(exception_handler)

        # 响应类型
        from pancake_web.response import JsonResponse, HtmlResponse
        export(JsonResponse)
        export(HtmlResponse)

        # 模板渲染
        from pancake_web.template import render, template, register_filter
        export(render)
        export(template)
        export(register_filter)

        # Web 服务器
        from pancake_web.server import WebServer
        export(WebServer)

        # 设置 WebServer 为主线程 loop_method
        from pancake import settings
        if not settings.get("framework.main_loop"):
            settings.set("framework.main_loop", "WebServer")

        logger.info("Web 插件已加载")

    def check(self) -> bool:
        """环境检查: 依赖 + 配置校验"""
        from pancake import settings

        # 1. 检查 aiohttp 依赖
        if not check_dependencies(["aiohttp"], extras="web"):
            return False

        # 2. 校验端口
        port = settings.get("pancake.web.port")
        try:
            port = int(port)
            if not (1 <= port <= 65535):
                raise ValueError
        except (ValueError, TypeError):
            logger.error(f"web.port 配置无效: {port}，必须是 1-65535 的整数")
            return False

        # 3. 校验 max_body_size
        max_body = settings.get("web.request.max_body_size")
        if max_body is not None:
            try:
                max_body = int(max_body)
                if max_body < 0:
                    raise ValueError
            except (ValueError, TypeError):
                logger.warning(f"web.request.max_body_size 配置无效: {max_body}，使用默认值 1MB")

        # 4. 校验静态文件目录（仅警告，不阻断）
        static_dir = settings.get("web.static")
        if static_dir:
            import os
            if not os.path.isdir(static_dir):
                logger.warning(f"静态文件目录不存在: {static_dir}，静态文件功能不可用")

        # 5. 校验模板目录（仅警告）
        template_dir = settings.get("web.templates")
        if template_dir:
            import os
            if not os.path.isdir(template_dir):
                logger.warning(f"模板目录不存在: {template_dir}")

        return True

    def build(self):
        pass
