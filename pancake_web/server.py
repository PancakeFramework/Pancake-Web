"""Web 服务器 — aiohttp 封装，支持 YAML 配置"""

import asyncio
import logging
import os

from aiohttp import web
from pancake.dough import Dough, Scope

logger = logging.getLogger(__name__)


class WebServer(Dough):
    """aiohttp Web 服务器

    配置项从 settings 读取（pancake.web.* 前缀），缺省值在插件内定义。
    用户可在 src/resource/yaml/ 的 YAML 中覆盖。
    """

    _scope = Scope.SINGLETON

    # 插件默认配置
    _defaults = {
        "pancake.web.host": "127.0.0.1",
        "pancake.web.port": 8080,
        "pancake.web.debug": False,
        "pancake.web.static": os.path.join("src", "static"),
        "pancake.web.templates": os.path.join("src", "templates"),
        "pancake.web.cors.allow_origins": "*",
        "pancake.web.cors.allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
        "pancake.web.cors.allow_headers": "*",
        "pancake.web.cors.max_age": 3600,
        "pancake.web.session.secret_key": None,
        "pancake.web.session.max_age": 86400,
        "pancake.web.session.secure": False,
        "pancake.web.request.timeout": 30,
        "pancake.web.request.max_body_size": 1048576,
        "pancake.web.server.max_connections": 100,
        "pancake.web.server.backlog": 128,
    }

    def _get(self, key):
        """获取配置：用户配置 > 插件默认值"""
        from pancake import settings
        val = settings.get(key)
        return val if val is not None else self._defaults.get(key)

    def __init__(self):
        super().__init__()

        self.host = self._get("pancake.web.host")
        self.port = self._get("pancake.web.port")
        self.debug = self._get("pancake.web.debug")
        self.static_dir = self._get("pancake.web.static")
        self.template_dir = self._get("pancake.web.templates")

        # CORS
        self.cors_origins = self._get("pancake.web.cors.allow_origins")
        self.cors_methods = self._get("pancake.web.cors.allow_methods")
        self.cors_headers = self._get("pancake.web.cors.allow_headers")
        self.cors_max_age = self._get("pancake.web.cors.max_age")

        # Session
        self.session_secret = self._get("pancake.web.session.secret_key")
        self.session_max_age = self._get("pancake.web.session.max_age")
        self.session_secure = self._get("pancake.web.session.secure")

        # Request
        self.request_timeout = self._get("pancake.web.request.timeout")
        self.max_body_size = self._get("pancake.web.request.max_body_size")

        # Server
        self.max_connections = self._get("pancake.web.server.max_connections")
        self.backlog = self._get("pancake.web.server.backlog")

        self._app = None
        self._runner = None

    def _create_app(self) -> web.Application:
        """创建 aiohttp 应用并注册路由、中间件"""
        from pancake_web.router import register_routes
        from pancake_web.middleware import build_aiohttp_middlewares
        from pancake_web.exception import create_error_middleware

        # 1. 构建中间件列表
        middlewares = []

        # CORS 中间件
        if self.cors_origins:
            middlewares.append(self._create_cors_middleware())

        # 异常处理中间件
        middlewares.append(create_error_middleware())

        # 用户注册的中间件
        middlewares.extend(build_aiohttp_middlewares())

        # 2. 创建 app
        app = web.Application(
            middlewares=middlewares,
            client_max_size=self.max_body_size,
        )

        # 3. 注册路由
        register_routes(app)

        # 4. 静态文件
        if self.static_dir and os.path.isdir(self.static_dir):
            app.router.add_static("/static", self.static_dir, show_index=False)
            logger.info(f"静态文件: /static -> {self.static_dir}")

        # 5. 存储配置供 handler 使用
        app["_template_dir"] = self.template_dir
        app["_debug"] = self.debug

        return app

    def _create_cors_middleware(self):
        """创建 CORS 中间件"""
        origins = self.cors_origins
        methods = self.cors_methods
        headers = self.cors_headers
        max_age = self.cors_max_age

        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == "OPTIONS":
                response = web.Response(status=204)
            else:
                try:
                    response = await handler(request)
                except web.HTTPException as exc:
                    response = exc

            origin = request.headers.get("Origin", "")
            if origins == "*" or origin in origins.split(","):
                response.headers["Access-Control-Allow-Origin"] = origin if origins != "*" else "*"
            response.headers["Access-Control-Allow-Methods"] = methods
            response.headers["Access-Control-Allow-Headers"] = headers
            response.headers["Access-Control-Max-Age"] = str(max_age)
            return response

        return cors_middleware

    async def start(self):
        """启动 Web 服务器"""
        self._app = self._create_app()
        self._runner = web.AppRunner(self._app, handle_signals=True)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self.host, int(self.port), backlog=self.backlog)
        await site.start()

        logger.info(f"Web 服务器已启动: http://{self.host}:{self.port}")
        if self.debug:
            logger.info("调试模式已开启")

    async def stop(self):
        """停止 Web 服务器"""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._app = None
            logger.info("Web 服务器已停止")

    def loop_method(self):
        """阻塞式运行 Web 服务器（供 run_loop 调用）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.start())
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(self.stop())
            loop.close()

    async def on_destroy(self):
        await self.stop()
