# 豆包 Seedance API 服务

基于豆包 AI 的视频生成 RESTful API 服务，支持**文生视频**和**图生视频**两种模式。

本服务为纯 API 版本，不包含 Gradio Web UI，适合作为后端接口服务部署。

## 功能特性

- **文生视频**：根据文本描述自动生成视频
- **图生视频**：基于参考图片生成视频
- **一体化接口**：图生视频支持上传+生成一步完成
- **自动轮询**：提交任务后自动等待视频生成完成
- **视频代理**：代理下载外网视频，解决国内网络访问问题
- **Cookie 负载均衡**：支持多账号 Round-Robin 轮询
- **Bearer Token 鉴权**：可选的 API 安全认证
- **Docker 部署**：支持容器化一键部署

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 创建 .env 文件
cat > .env << 'EOF'
DOUBAO_SESSION_COOKIE=your_cookie_here
AUTH_TOKEN=sk-your-token-here
EOF

# 2. 构建并启动
docker-compose up -d --build

# 3. 查看日志
docker-compose logs -f

# 4. 测试服务
curl http://localhost:8000/
```

### 方式二：本地运行

```bash
# 1. 安装依赖
pip install -r requirements-api.txt

# 2. 配置环境变量
export DOUBAO_SESSION_COOKIE="your_cookie_here"
export AUTH_TOKEN="sk-your-token-here"  # 可选

# 3. 启动服务
python api.py
# 或
uvicorn api:app --host 0.0.0.0 --port 8000
```

## 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `DOUBAO_BASE_URL` | 豆包 API 地址 | https://doubao.happieapi.top | 否 |
| `DOUBAO_SESSION_COOKIE` | Session Cookie（支持逗号分隔多个） | - | **是** |
| `AUTH_TOKEN` | API 鉴权 Token（支持逗号分隔多个） | - | 否 |
| `API_HOST` | 服务监听地址 | 0.0.0.0 | 否 |
| `API_PORT` | 服务监听端口 | 8000 | 否 |

### 获取 Cookie

1. 打开浏览器访问 https://doubao.happieapi.top
2. 登录账号
3. 打开开发者工具 (F12) → Application → Cookies
4. 复制 `connect.sid` 的值

## API 鉴权

配置 `AUTH_TOKEN` 后，所有接口（除健康检查外）需要携带鉴权头：

```
Authorization: Bearer <your-token>
```

**特性说明：**
- 不配置 `AUTH_TOKEN` 则跳过鉴权（向后兼容）
- 支持多个 Token，用逗号分隔：`AUTH_TOKEN=token1,token2,token3`
- 健康检查接口 `GET /` 无需鉴权

## API 接口文档

### 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **交互式文档**: `http://localhost:8000/docs`

### 接口列表

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/` | 健康检查 | 否 |
| GET | `/proxy/{url}` | 视频代理下载 | 否 |
| POST | `/api/upload` | 上传图片 | 是 |
| POST | `/api/video/create` | 创建视频任务 | 是 |
| POST | `/api/video/create-with-image` | 图生视频一体化 | 是 |
| POST | `/api/video/create-and-wait` | 创建并等待完成 | 是 |
| GET | `/api/videos` | 获取视频列表 | 是 |
| GET | `/api/video/{video_id}/status` | 查询视频状态 | 是 |
| GET | `/api/stats/video-count` | 获取视频统计 | 是 |

---

### 1. 健康检查

**GET /**

```bash
curl http://localhost:8000/
```

**响应示例：**
```json
{
  "service": "豆包 Seedance 视频生成 API",
  "version": "1.0.0",
  "cookie_count": 2,
  "load_balance": "round-robin",
  "auth_enabled": true,
  "endpoints": {
    "upload": "POST /api/upload - 上传图片",
    "create_video": "POST /api/video/create - 创建视频",
    "list_videos": "GET /api/videos - 获取视频列表",
    "video_count": "GET /api/stats/video-count - 获取视频统计",
    "video_status": "GET /api/video/{video_id}/status - 查询视频状态"
  }
}
```

---

### 2. 上传图片

**POST /api/upload**

用于图生视频模式，上传图片后获取图片 URL。

```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer sk-your-token" \
  -F "file=@./image.png"
```

**响应示例：**
```json
{
  "success": true,
  "message": "上传成功",
  "url": "https://example.com/uploaded-image.png",
  "data": {
    "ok": true,
    "url": "https://example.com/uploaded-image.png"
  }
}
```

---

### 3. 创建视频

**POST /api/video/create**

支持文生视频和图生视频两种模式。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 否 | 模型名称，默认 `seedance-1-5-pro-251215` |
| prompt | string | **是** | 视频描述提示词 |
| duration | int | 否 | 视频时长(秒)，默认 5，范围 1-10 |
| radio | string | 否 | 视频比例，默认 `16:9` |
| image | string | 否 | 图片URL（图生视频时必填） |

**文生视频示例：**
```bash
curl -X POST http://localhost:8000/api/video/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-token" \
  -d '{
    "model": "seedance-1-5-pro-251215",
    "prompt": "一只可爱的猫咪在草地上奔跑",
    "duration": 5,
    "radio": "16:9"
  }'
```

**图生视频示例：**
```bash
curl -X POST http://localhost:8000/api/video/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-token" \
  -d '{
    "model": "seedance-1-5-pro-251215",
    "prompt": "让图片中的人物微笑并挥手",
    "duration": 5,
    "radio": "16:9",
    "image": "https://example.com/your-image.png"
  }'
```

**响应示例：**
```json
{
  "success": true,
  "message": "视频创建任务已提交 (文生视频)",
  "data": {
    "taskId": "12345678",
    "status": "pending"
  }
}
```

---

### 4. 图生视频一体化

**POST /api/video/create-with-image**

自动完成图片上传并创建视频，一步到位。

```bash
curl -X POST http://localhost:8000/api/video/create-with-image \
  -H "Authorization: Bearer sk-your-token" \
  -F "prompt=让图片中的角色动起来" \
  -F "file=@./character.png" \
  -F "model=seedance-1-5-pro-251215" \
  -F "duration=5" \
  -F "radio=16:9"
```

**响应示例：**
```json
{
  "success": true,
  "message": "图生视频任务已提交",
  "data": {
    "image_url": "https://example.com/uploaded-image.png",
    "video_task": {
      "taskId": "12345678",
      "status": "pending"
    }
  }
}
```

---

### 5. 创建视频并等待完成

**POST /api/video/create-and-wait**

创建视频后自动轮询状态，直到生成完成或超时。

**额外参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| max_wait_seconds | int | 否 | 最大等待时间(秒)，默认 300 |
| poll_interval | int | 否 | 轮询间隔(秒)，默认 5 |

```bash
curl -X POST "http://localhost:8000/api/video/create-and-wait?max_wait_seconds=600&poll_interval=10" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-token" \
  -d '{
    "prompt": "夜晚的赛博朋克城市，霓虹灯闪烁",
    "duration": 5,
    "radio": "16:9"
  }'
```

**成功响应：**
```json
{
  "success": true,
  "message": "视频生成完成",
  "video_url": "https://example.com/generated-video.mp4",
  "data": {
    "id": "12345678",
    "status": "completed",
    "videoUrl": "https://example.com/generated-video.mp4"
  }
}
```

**超时响应：**
```json
{
  "success": false,
  "message": "等待超时(300秒)，请稍后手动查询",
  "task_id": "12345678"
}
```

---

### 6. 获取视频列表

**GET /api/videos**

```bash
curl -X GET http://localhost:8000/api/videos \
  -H "Authorization: Bearer sk-your-token"
```

**响应示例：**
```json
{
  "success": true,
  "data": [
    {
      "id": "12345678",
      "prompt": "一只猫咪在草地上奔跑",
      "status": "completed",
      "videoUrl": "https://example.com/video1.mp4",
      "createdAt": "2024-01-01T12:00:00Z"
    },
    {
      "id": "12345679",
      "prompt": "日落海滩",
      "status": "processing",
      "videoUrl": null,
      "createdAt": "2024-01-01T12:30:00Z"
    }
  ]
}
```

---

### 7. 查询视频状态

**GET /api/video/{video_id}/status**

```bash
curl -X GET http://localhost:8000/api/video/12345678/status \
  -H "Authorization: Bearer sk-your-token"
```

**响应示例：**
```json
{
  "success": true,
  "status": "completed",
  "video_url": "https://example.com/generated-video.mp4",
  "data": {
    "id": "12345678",
    "prompt": "一只猫咪在草地上奔跑",
    "status": "completed",
    "videoUrl": "https://example.com/generated-video.mp4"
  }
}
```

**状态说明：**
| 状态值 | 说明 |
|--------|------|
| pending | 等待处理 |
| processing | 生成中 |
| completed | 生成完成 |
| failed | 生成失败 |

---

### 8. 获取视频统计

**GET /api/stats/video-count**

```bash
curl -X GET http://localhost:8000/api/stats/video-count \
  -H "Authorization: Bearer sk-your-token"
```

**响应示例：**
```json
{
  "success": true,
  "data": {
    "total": 100,
    "completed": 95,
    "processing": 3,
    "failed": 2
  }
}
```

---

## 模型与参数

### 可用模型

| 模型名称 | 说明 |
|----------|------|
| `seedance-1-5-pro-251215` | 最新模型，支持声音（推荐） |
| `seedance-1-0-pro-fast` | 快速模型 |

### 视频时长

支持 `4s`、`5s`、`8s`、`12s`

### 视频比例

| 比例 | 说明 |
|------|------|
| `21:9` | 超宽银幕（电影） |
| `16:9` | 横屏（默认） |
| `4:3` | 经典比例 |
| `1:1` | 正方形（社交媒体） |
| `3:4` | 竖屏偏方 |
| `9:16` | 竖屏（抖音/Shorts） |

---

## Docker 部署详解

### 目录结构

```
server/
├── api.py                # API 服务主文件
├── Dockerfile            # Docker 镜像构建文件
├── docker-compose.yml    # Docker Compose 编排文件
├── requirements-api.txt  # Python 依赖
├── .env                  # 环境变量配置（需创建）
└── README.md             # 本文档
```

### 构建镜像

```bash
# 使用 Docker Compose 构建
docker-compose build

# 或手动构建
docker build -t seedance-api:latest .
```

### 运行容器

```bash
# 使用 Docker Compose（推荐）
docker-compose up -d

# 或手动运行
docker run -d \
  --name seedance-api \
  -p 8000:8000 \
  -e DOUBAO_SESSION_COOKIE="your_cookie_here" \
  -e AUTH_TOKEN="sk-your-token" \
  seedance-api:latest
  
# 直接接拉取并运行
docker run -d \
  --name seedance-api \
  -p 8000:8000 \
  -e DOUBAO_SESSION_COOKIE="your_cookie_here" \
  -e AUTH_TOKEN="sk-your-token" \
  wwwzhouhui569/seedance-api:latest
```

### 常用命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 查看容器状态
docker-compose ps

# 进入容器
docker exec -it seedance-api /bin/bash
```

### 健康检查

容器内置健康检查，每 30 秒检测一次：

```bash
# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' seedance-api

# 手动测试
curl -f http://localhost:8000/
```

---

## 错误处理

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 401 | 未授权：缺少 Authorization 头或 Token 格式错误 |
| 403 | 禁止访问：Token 无效或已过期 |
| 500 | 服务器错误：请查看日志排查 |

### 错误响应格式

```json
{
  "detail": "Missing Authorization Header. Please provide 'Authorization: Bearer <token>'"
}
```

---

## 与主项目区别

| 特性 | 主项目 (根目录) | Server API |
|------|----------------|------------|
| 服务类型 | Gradio UI + API | 仅 API |
| 默认端口 | 7860 | 8000 |
| 依赖项 | 包含 Gradio | 不含 Gradio |
| 镜像大小 | ~1.5GB | ~300MB |
| 适用场景 | 完整可视化服务 | 后端接口服务 |

---

## 依赖说明

```
fastapi>=0.116.1       # Web 框架
uvicorn[standard]      # ASGI 服务器
httpx>=0.26.0          # 异步 HTTP 客户端
pydantic>=2.5.3        # 数据验证
python-multipart       # 文件上传支持
python-dotenv          # 环境变量加载
```

---

## 免责声明

本项目仅供学习和研究使用，请勿用于商业用途。使用本项目产生的任何问题由使用者自行承担。

## License

MIT License
