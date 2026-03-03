# 豆包 Seedance 1.5 Pro 视频生成

> 基于豆包 AI 的视频生成服务，支持文生视频和图生视频两种模式，提供 Gradio Web UI 和 RESTful API 两种使用方式

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.116+-green.svg)
![Gradio](https://img.shields.io/badge/gradio-6.0+-orange.svg)

---

## 在线体验

无需部署，直接访问体验：

| 访问方式 | 地址 |
|---------|------|
| 🦆 SCNet AIHub | https://www.scnet.cn/ui/aihub/agent/wwxiaohuihui/doubao-seedance-ttv-itv?id=2005197391799721985 |

⚡ 即开即用，体验 AI 视频生成！

---

## 项目介绍

豆包 Seedance 1.5 Pro 视频生成是一个专业的 AI 驱动视频生成服务，基于豆包 AI 的 Seedance 模型，让每个人都能快速创作出高质量的视频内容。

### 核心特性

- **文生视频**: 根据文本描述自动生成视频
- **图生视频**: 基于参考图片生成视频
- **Gradio Web UI**: 可视化界面，支持参数配置、实时进度显示、视频播放和下载
- **RESTful API**: 标准 API 接口，支持集成到第三方应用
- **自动轮询**: 提交任务后自动等待视频生成完成
- **视频代理下载**: 内置 API 服务代理下载，解决国内网络无法访问外网视频 URL 的问题
- **Cookie 负载均衡**: 支持多账号轮询，提高并发能力
- **Docker 部署**: 支持容器化一键部署

---

## 功能清单

| 功能名称 | 功能说明 | 技术栈 | 状态 |
|---------|---------|--------|------|
| 文生视频 | 根据文本描述自动生成视频 | FastAPI + httpx | ✅ 稳定 |
| 图生视频 | 基于参考图片生成视频 | FastAPI + Pillow | ✅ 稳定 |
| Gradio Web UI | 可视化界面操作 | Gradio 6.0+ | ✅ 稳定 |
| RESTful API | 标准 API 接口 | FastAPI 0.116+ | ✅ 稳定 |
| 自动轮询 | 任务完成后自动获取结果 | Python | ✅ 稳定 |
| 视频代理下载 | 代理下载外网视频 | httpx | ✅ 稳定 |
| Cookie 负载均衡 | 多账号轮询提高并发 | Python | ✅ 稳定 |
| API 鉴权 | Token 鉴权保护接口 | FastAPI | ✅ 稳定 |
| Docker 部署 | 一键容器化部署 | Docker + Compose | ✅ 稳定 |

---

## 技术架构

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 主要开发语言 |
| FastAPI | 0.116+ | Web 框架 |
| Gradio | 6.0+ | Web UI 框架 |
| httpx | 0.26+ | 异步 HTTP 客户端 |
| Uvicorn | 0.35+ | ASGI 服务器 |
| Pydantic | 2.5+ | 数据验证 |

---

## 容器架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            容器架构图                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────────┐       ┌─────────────────────────┐       ┌─────────────┐ │
│   │   Gradio Web UI  │ ◄────► │   FastAPI Backend      │ ◄────► │  豆包 API   │ │
│   │   端口 7860       │       │   端口 8000             │       │  (视频生成)  │ │
│   └──────────────────┘       └─────────────────────────┘       └─────────────┘ │
│           │                            │                              │        │
│           ▼                            ▼                              ▼        │
│   Web 可视化界面            API 接口 + 视频代理                Seedance AI      │
│   用户参数配置              自动轮询任务状态                 文生视频/图生视频    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 安装说明

### 环境要求

- Python 3.8+
- pip 包管理器
- Docker / Docker Compose（可选）

### 安装依赖

```bash
pip install -r requirements.txt
```

---

## 使用说明

### 基础使用

```
配置环境变量 → 启动服务 → Web UI 或 API 调用 → 下载视频
```

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 Session Cookie：

```env
# 豆包API配置
DOUBAO_BASE_URL=https://doubao.happieapi.top
# 支持多个cookie用逗号分隔，实现负载均衡
DOUBAO_SESSION_COOKIE=cookie1,cookie2

# 服务配置
ENABLE_INTERNAL_API=true
API_PORT=8000
GRADIO_PORT=7860
```

**获取 Cookie 方法：**
1. 打开浏览器访问 https://doubao.happieapi.top
2. 登录账号
3. 打开开发者工具 (F12) -> Application -> Cookies
4. 复制 `connect.sid` 的值

### 2. 启动服务

**方式一：Gradio Web UI（推荐）**

```bash
python app.py
```

启动后会自动：
1. 启动内置 API 服务 (端口 8000)
2. 启动 Gradio 前端 (端口 7860)

访问 http://localhost:7860 使用 Web 界面。

**方式二：仅启动 API 服务**

```bash
cd server
python api.py
# 或
uvicorn api:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 3. 使用命令行客户端

```bash
cd client

# 文生视频（自动等待完成）
python client.py text2video "一只可爱的猫咪在草地上奔跑"

# 文生视频并下载
python client.py text2video "夜晚的赛博朋克城市" -d

# 图生视频
python client.py image2video "小鸟飞翔" ./bird.png -d
```

---

## Web UI 使用说明

### 界面预览

![Web UI 界面](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251228162721843.png)

### 视频效果

![视频效果示例](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/401df43a-ea51-45a6-9192-bc072c368480.gif)

### 参数说明

| 参数 | 选项 | 说明 |
|------|------|------|
| 模型 | seedance-1-5-pro-251215 | 最新模型，支持声音 |
| | seedance-1-0-pro-fast | 快速模型 |
| 时长 | 4s, 5s, 8s, 12s | 视频时长 |
| 比例 | 21:9 (超宽银幕) | 电影宽银幕 |
| | 16:9 (横屏·默认) | 标准横屏 |
| | 4:3 (经典比例) | 传统比例 |
| | 1:1 (正方形) | 社交媒体 |
| | 3:4 (竖屏偏方) | 竖版照片 |
| | 9:16 (竖屏·抖音/Shorts) | 短视频平台 |

---

## 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DOUBAO_BASE_URL` | 豆包 API 地址 | https://doubao.happieapi.top |
| `DOUBAO_SESSION_COOKIE` | Session Cookie (支持逗号分隔多个) | 必填 |
| `AUTH_TOKEN` | API鉴权Token (支持逗号分隔多个) | 可选 |
| `ENABLE_INTERNAL_API` | 是否启动内置API | true |
| `API_HOST` | API 监听地址 | 0.0.0.0 |
| `API_PORT` | API 监听端口 | 8000 |
| `GRADIO_PORT` | Gradio 监听端口 | 7860 |
| `TZ` | 时区 | Asia/Shanghai |

### API 鉴权

配置 `AUTH_TOKEN` 后，所有 API 接口（除健康检查外）需要携带鉴权头：

```bash
Authorization: Bearer <your-token>
```

**示例：**

```bash
# 带鉴权的 API 请求
curl -X POST http://localhost:8000/api/video/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-doubao-video-2024" \
  -d '{"model": "seedance-1-5-pro-251215", "prompt": "一只猫咪", "duration": 5, "radio": "16:9"}'

# 客户端使用 --token 参数
cd client
python client.py --token sk-doubao-video-2024 text2video "一只猫咪"

# 或通过环境变量
export AUTH_TOKEN=sk-doubao-video-2024
python client.py text2video "一只猫咪"
```

---

## 项目结构

```
doubao-seedance-ttv-itv/
├── app.py                    # Gradio Web UI (自动启动内置API服务)
├── requirements.txt          # 依赖包
├── .env.example              # 环境变量示例
├── Dockerfile                # Docker 镜像构建文件 (Gradio + API + 视频代理)
├── docker-compose.yml        # Docker Compose 编排文件 (生产环境)
├── docker-compose-dev.yml    # Docker Compose 开发构建文件
├── README.md                 # 说明文档
├── server/                   # API 服务模块
│   ├── api.py                # FastAPI 后端服务 (含视频代理接口)
│   ├── Dockerfile            # API 独立 Docker 镜像
│   ├── docker-compose.yml    # API 独立部署配置
│   ├── requirements-api.txt  # API 依赖包
│   └── README.md             # API 服务文档
├── client/                   # 客户端模块
│   ├── app.py                # Gradio 客户端 (远程API版)
│   ├── client.py             # Python 命令行客户端
│   └── clientcurl.txt        # Curl 命令示例
└── curl/                     # Curl 示例目录
```

---

## 开发指南

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动 Gradio Web UI
python app.py

# 或仅启动 API 服务
cd server
python api.py
```

### Docker 开发

```bash
# 使用 Docker Hub 镜像（推荐）
docker run -d \
  --name doubao-seedance \
  -p 7860:7860 \
  -e DOUBAO_SESSION_COOKIE="your_cookie_here" \
  -e AUTH_TOKEN="sk-your-secret-token-here" \
  wwwzhouhui569/doubao-seedance:latest

# 查看日志
docker logs -f doubao-seedance

# 停止容器
docker stop doubao-seedance

# 删除容器
docker rm doubao-seedance
```

### 使用 Docker Compose

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DOUBAO_SESSION_COOKIE

# 2. 构建并启动
docker-compose up -d --build

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

### 手动构建镜像

```bash
# 构建镜像
docker build -t doubao-seedance:latest .

# 运行容器
docker run -d \
  --name doubao-seedance \
  -p 7860:7860 \
  -e DOUBAO_SESSION_COOKIE="your_cookie_here" \
  -e AUTH_TOKEN="sk-your-secret-token-here" \
  doubao-seedance:latest
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| GET | `/proxy/{url}` | 视频代理下载 |
| POST | `/api/upload` | 上传图片 |
| POST | `/api/video/create` | 创建视频任务 |
| POST | `/api/video/create-with-image` | 图生视频一体化 |
| POST | `/api/video/create-and-wait` | 创建并等待完成 |
| GET | `/api/videos` | 获取视频列表 |
| GET | `/api/video/{video_id}/status` | 查询视频状态 |

### 创建视频示例

```bash
# 如果配置了 AUTH_TOKEN，需要添加鉴权头
curl -X POST http://localhost:8000/api/video/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-doubao-video-2024" \
  -d '{
    "model": "seedance-1-5-pro-251215",
    "prompt": "一只可爱的猫咪在草地上奔跑",
    "duration": 5,
    "radio": "16:9"
  }'
```

### 视频代理下载示例

```bash
# 当视频URL无法直接访问时，使用代理下载
# 原始URL: https://ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com/xxx.mp4
# 代理URL: http://localhost:8000/proxy/https://ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com/xxx.mp4

curl -o video.mp4 "http://localhost:8000/proxy/https://ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com/xxx.mp4"
```

---

## Python SDK

```python
# 将 client/client.py 添加到项目或复制到项目目录
from client import DoubaoVideoClient

# 如果配置了 AUTH_TOKEN，需要传入 auth_token 参数
with DoubaoVideoClient("http://localhost:8000", auth_token="sk-doubao-video-2024") as client:
    # 创建并等待完成
    result = client.create_and_wait(
        prompt="日落海滩",
        max_wait_seconds=600
    )

    if result.get("success"):
        video_url = result.get("video_url")
        client.download_video(video_url, "output.mp4")
```

---

## 常见问题

<details>
<summary>Q: 提示未配置 SESSION_COOKIE？</summary>

A: 确保 `.env` 文件中正确配置了 `DOUBAO_SESSION_COOKIE`，且 Cookie 未过期。
</details>

<details>
<summary>Q: 内置API未启动？</summary>

A: 检查 `ENABLE_INTERNAL_API` 是否设置为 `true`，以及 `server/api.py` 文件是否存在。
</details>

<details>
<summary>Q: 视频下载失败？</summary>

A: 国内网络可能无法直接访问视频URL（`ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com`）。容器部署时会自动使用内置API的代理功能下载视频。如果代理下载也失败，可以复制提示的代理URL手动下载。
</details>

<details>
<summary>Q: 视频生成超时？</summary>

A: 增加 `--timeout` 参数值，或使用 `--no-wait` 提交任务后手动查询状态。
</details>

<details>
<summary>Q: 端口被占用？</summary>

A: 使用以下命令杀掉占用端口的进程：
```bash
fuser -k 7860/tcp
fuser -k 8000/tcp
```
或使用其他端口：
```bash
GRADIO_PORT=7861 python app.py
```
</details>

---

## 技术交流群

欢迎加入技术交流群，分享你的使用心得和反馈建议：

![技术交流群](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20260303214419_166_292.jpg)

---

## 作者联系

- **微信**: laohaibao2025
- **邮箱**: 75271002@qq.com

![微信二维码](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Screenshot_20260123_095617_com.tencent.mm.jpg)

---

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

**微信支付**

![微信支付](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

---

## Star History

如果觉得项目不错，欢迎点个 Star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=wwwzhouhui/doubao-seedance-ttv-itv&type=Date)](https://star-history.com/#wwwzhouhui/doubao-seedance-ttv-itv&Date)

---

## License

MIT License

---

## 免责声明

本项目仅供学习和研究使用，请勿用于商业用途。使用本项目产生的任何问题由使用者自行承担。
