"""模板渲染 — Jinja2 引擎封装"""

import logging
import os

from jinja2 import Environment, FileSystemLoader

from pancake_web.response import HtmlResponse

logger = logging.getLogger(__name__)

_env: Environment = None


def _get_env() -> Environment:
    """获取或创建 Jinja2 Environment（单例）"""
    global _env
    if _env is None:
        from pancake import settings

        template_dir = settings.get("pancake.web.templates") or os.path.join("src", "templates")
        debug = settings.get("pancake.web.debug") or False

        if not os.path.isdir(template_dir):
            os.makedirs(template_dir, exist_ok=True)
            logger.info(f"模板目录已创建: {template_dir}")

        loader = FileSystemLoader(template_dir)
        _env = Environment(loader=loader, auto_reload=debug)
        logger.info(f"Jinja2 引擎已初始化: {template_dir}")
    return _env


def render(template_name: str, **context) -> HtmlResponse:
    """手动渲染模板，返回 HtmlResponse

    Usage:
        return render("home.html", title="首页", items=[1, 2, 3])
    """
    env = _get_env()
    tmpl = env.get_template(template_name)
    html = tmpl.render(**context)
    return HtmlResponse(html)


def template(template_name: str):
    """@template — handler 返回 dict 自动渲染为 HTML 页面

    Usage:
        @get("/home")
        @template("home.html")
        async def home(self, request):
            return {"title": "首页", "items": [1, 2, 3]}
    """
    def decorator(func):
        func._template_name = template_name
        return func
    return decorator


def register_filter(name: str, func):
    """注册 Jinja2 自定义过滤器

    Usage:
        register_filter("reverse", lambda s: s[::-1])
    """
    env = _get_env()
    env.filters[name] = func
    logger.debug(f"注册模板过滤器: {name}")


def reset_env():
    """重置 Jinja2 环境（用于测试）"""
    global _env
    _env = None
