# 豆包 Seedance 1.5 Pro 视频生成

基于豆包 AI 的视频生成服务，支持**文生视频**和**图生视频**两种模式，提供 **Gradio Web UI** 和 **RESTful API** 两种使用方式。

**体验地址：** [立即使用](https://www.scnet.cn/ui/aihub/agent/wwxiaohuihui/doubao-seedance-ttv-itv?id=2005197391799721985)

## 功能特性

- **Gradio Web UI**：可视化界面，支持参数配置、实时进度显示、视频播放和下载
- **文生视频**：根据文本描述自动生成视频
- **图生视频**：基于参考图片生成视频
- **自动轮询**：提交任务后自动等待视频生成完成
- **视频代理下载**：内置API服务代理下载，解决国内网络无法访问外网视频URL的问题
- **Cookie负载均衡**：支持多账号轮询，提高并发能力
- **Docker部署**：支持容器化一键部署

## 目录结构

```
doubao-seedance-1-5-pro/
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

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

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

### 3. 启动服务

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

> 详细 API 文档请参考 [server/README.md](./server/README.md)

### 4. 使用命令行客户端

```bash
cd client

# 文生视频（自动等待完成）
python client.py text2video "一只可爱的猫咪在草地上奔跑"

# 文生视频并下载
python client.py text2video "夜晚的赛博朋克城市" -d

# 图生视频
python client.py image2video "小鸟飞翔" ./bird.png -d
```

## Web UI 使用说明

### 界面预览

![image-20251228162721843](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251228162721843.png)

视频效果

![401df43a-ea51-45a6-9192-bc072c368480](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/401df43a-ea51-45a6-9192-bc072c368480.gif)

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

## Docker 部署

### 使用 Docker Hub 镜像（推荐）

```bash
# 直接拉取并运行
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

### 容器架构

![1766938138202](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/1766938138202.png)

- **app.py** 启动时自动加载 **server/api.py** 作为子进程
- 容器内部通过 `localhost:8000` 通信
- 内置 API 服务提供 `/proxy/{url}` 视频代理下载功能
- 只需暴露 `7860` 端口给外部访问

### 环境变量

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

## API 鉴权

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

## 客户端命令

> 客户端位于 `client/` 目录，使用前请先 `cd client`

### 文生视频

```bash
python client.py text2video <prompt> [options]
# 简写
python client.py t2v <prompt> [options]
```

**参数：**
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `prompt` | 视频描述提示词 | 必填 |
| `--model` | 模型名称 | seedance-1-5-pro-251215 |
| `--duration` | 视频时长(秒) | 5 |
| `--radio` | 视频比例 | 16:9 |
| `--no-wait` | 不等待视频生成完成 | - |
| `--timeout` | 最大等待时间(秒) | 600 |
| `-d, --download` | 下载视频到本地 | - |
| `-o, --output` | 指定输出文件路径 | - |

### 图生视频

```bash
python client.py image2video <prompt> <image> [options]
# 简写
python client.py i2v <prompt> <image> [options]
```

### 其他命令

```bash
# 获取视频列表
python client.py list

# 查询视频状态
python client.py status <task_id>

# 等待任务完成
python client.py wait <task_id> -d

# 下载视频
python client.py download <video_url> -o output.mp4
```

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

## 常见问题

### 1. 提示未配置 SESSION_COOKIE

确保 `.env` 文件中正确配置了 `DOUBAO_SESSION_COOKIE`，且 Cookie 未过期。

### 2. 内置API未启动

检查 `ENABLE_INTERNAL_API` 是否设置为 `true`，以及 `server/api.py` 文件是否存在。

### 3. 视频下载失败

- 国内网络可能无法直接访问视频URL（`ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com`）
- 容器部署时会自动使用内置API的代理功能下载视频
- 如果代理下载也失败，可以复制提示的代理URL手动下载

### 4. 视频生成超时

- 增加 `--timeout` 参数值
- 使用 `--no-wait` 提交任务后手动查询状态

### 5. 端口被占用

```bash
# 杀掉占用端口的进程
fuser -k 7860/tcp
fuser -k 8000/tcp

# 或使用其他端口
GRADIO_PORT=7861 python app.py
```

## 依赖说明

```
fastapi>=0.116.1       # Web框架
uvicorn[standard]      # ASGI服务器
httpx>=0.26.0          # HTTP客户端
gradio>=5.0.0          # Web UI框架
pydantic>=2.5.3        # 数据验证
python-multipart       # 文件上传
python-dotenv          # 环境变量
```

## 免责声明

本项目仅供学习和研究使用，请勿用于商业用途。使用本项目产生的任何问题由使用者自行承担。

## License

MIT License
