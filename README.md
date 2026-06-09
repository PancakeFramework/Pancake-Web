# pancake-web

Spring MVC 风格的 Web 服务器插件，基于 aiohttp。

## 安装

```bash
pip install pancake-web
```

依赖自动安装 `aiohttp`。

## 快速开始

### 1. 配置 YAML

在 `src/resource/yaml/web.yaml` 中配置（所有配置项都有缺省值，可省略）：

```yaml
web:
  host: 127.0.0.1
  port: 8080
  debug: false
  static: src/static
  templates: src/templates
  cors:
    allow_origins: "*"
    allow_methods: "GET,POST,PUT,DELETE,OPTIONS"
    allow_headers: "*"
    max_age: 3600
  session:
    secret_key: my-secret-key
    max_age: 86400
    secure: false
  request:
    timeout: 30
    max_body_size: 1048576
  server:
    max_connections: 100
    backlog: 128
```

### 2. 创建控制器

`src/controller/user_controller.py`：

```python
from dataclasses import dataclass

@controller("/api/users")
class UserController:
    user_service: UserService = inject()

    @get("/")
    async def list_users(self, request):
        return self.user_service.find_all()

    @get("/{id}")
    async def get_user(self, request, id: int = path_variable()):
        return self.user_service.find_by_id(id)

    @post("/")
    async def create_user(self, request, body: CreateUserForm = request_body()):
        return self.user_service.create(body), 201

    @delete("/{id}")
    async def delete_user(self, request, id: int = path_variable()):
        self.user_service.delete(id)

@dataclass
class CreateUserForm:
    name: str
    age: int = 0
```

### 3. 启动

```bash
python main.py
```

访问 `http://127.0.0.1:8080/api/users`。

## YAML 配置项

| 配置键 | 类型 | 缺省值 | 说明 |
|--------|------|--------|------|
| `web.host` | str | `127.0.0.1` | 服务器地址 |
| `web.port` | int | `8080` | 服务器端口 |
| `web.debug` | bool | `false` | 调试模式 |
| `web.static` | str | `src/static` | 静态文件目录 |
| `web.templates` | str | `src/templates` | 模板目录 |
| `web.cors.allow_origins` | str | `*` | CORS 允许来源 |
| `web.cors.allow_methods` | str | `GET,POST,PUT,DELETE,OPTIONS` | CORS 允许方法 |
| `web.cors.allow_headers` | str | `*` | CORS 允许头 |
| `web.cors.max_age` | int | `3600` | 预检缓存秒数 |
| `web.session.secret_key` | str | `null` | Session 密钥 |
| `web.session.max_age` | int | `86400` | Session 有效期 |
| `web.session.secure` | bool | `false` | 仅 HTTPS |
| `web.request.timeout` | int | `30` | 请求超时秒数 |
| `web.request.max_body_size` | int | `1048576` | 最大请求体字节 |
| `web.server.max_connections` | int | `100` | 最大连接数 |
| `web.server.backlog` | int | `128` | TCP backlog |

## 装饰器

### 路由

| 装饰器 | 用途 |
|--------|------|
| `@controller(prefix)` | 标记类为控制器（自动注册为 Dough，支持 IoC） |
| `@get(path)` | GET 路由 |
| `@post(path)` | POST 路由 |
| `@put(path)` | PUT 路由 |
| `@delete(path)` | DELETE 路由 |

### 参数绑定

| 标记 | 用途 |
|------|------|
| `path_variable()` | 路径变量 `/users/{id}` |
| `request_param(name, default)` | 查询参数 `?page=1` |
| `request_body()` | JSON 请求体（支持 dataclass/Struct） |

### 中间件与异常

| 装饰器 | 用途 |
|--------|------|
| `@middleware(order)` | 注册中间件（order 越小越先执行） |
| `@exception_handler(exc_class)` | 注册全局异常处理器 |

## 返回值自动转换

| 返回类型 | 转换结果 |
|---------|---------|
| `dict` / `list` | JSON 响应 |
| `str` | HTML 响应 |
| `dataclass` / `Struct` | JSON 响应（自动 asdict） |
| `(data, status)` | 指定状态码的 JSON |
| `(data, status, headers)` | 指定状态码和响应头 |
| `None` | 204 No Content |
| `web.Response` | 原样返回 |

## 示例：中间件

```python
@middleware(order=0)
class LoggingMiddleware:
    async def process(self, request, handler):
        logger.info(f"{request.method} {request.path}")
        response = await handler(request)
        logger.info(f"响应: {response.status}")
        return response
```

## 示例：异常处理

```python
@exception_handler(ValueError)
async def handle_value_error(request, exc):
    return JsonResponse({"error": str(exc)}, status=400)

@exception_handler(PermissionError)
async def handle_permission(request, exc):
    return JsonResponse({"error": "无权限"}, status=403)
```
