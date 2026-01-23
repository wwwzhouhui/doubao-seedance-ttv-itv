"""
豆包 Seedance 1.5 Pro 视频生成 逆向API服务
支持文生视频和图生视频两种模式
"""

import os
import asyncio
import itertools
import threading
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv
from urllib.parse import unquote

load_dotenv()

app = FastAPI(
    title="豆包 Seedance 视频生成 API",
    description="基于豆包 AI 的视频生成逆向接口，支持文生视频和图生视频",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
BASE_URL = os.getenv("DOUBAO_BASE_URL", "https://doubao.happieapi.top")
SESSION_COOKIES_RAW = os.getenv("DOUBAO_SESSION_COOKIE", "")

# API鉴权Token (支持多个token，逗号分隔)
AUTH_TOKENS_RAW = os.getenv("AUTH_TOKEN", "")
AUTH_TOKENS: List[str] = [t.strip() for t in AUTH_TOKENS_RAW.split(",") if t.strip()]

# 解析多个cookie，支持逗号分隔
SESSION_COOKIES: List[str] = [unquote(c.strip()) for c in SESSION_COOKIES_RAW.split(",") if c.strip()]


# ==================== 鉴权依赖 ====================

def verify_auth_token(authorization: str = Header(None)) -> str:
    """
    验证 Authorization Header 中的 Bearer Token

    如果未配置AUTH_TOKEN，则跳过鉴权（向后兼容）
    """
    # 如果未配置AUTH_TOKEN，跳过鉴权
    if not AUTH_TOKENS:
        return None

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization Header. Please provide 'Authorization: Bearer <token>'"
        )

    # 解析 Bearer Token
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization Scheme. Expected 'Bearer <token>'"
        )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing Token in Authorization Header"
        )

    # 验证token是否有效
    if token not in AUTH_TOKENS:
        raise HTTPException(
            status_code=403,
            detail="Invalid or Expired Token"
        )

    return token

# Cookie轮询选择器 (线程安全的Round-Robin)
class CookieSelector:
    def __init__(self, cookies: List[str]):
        self.cookies = cookies
        self._cycle = itertools.cycle(cookies) if cookies else None
        self._lock = threading.Lock()

    def get_next(self) -> Optional[str]:
        """获取下一个cookie (Round-Robin负载均衡)"""
        if not self._cycle:
            return None
        with self._lock:
            return next(self._cycle)

    def get_all(self) -> List[str]:
        """获取所有cookie列表"""
        return self.cookies

    def count(self) -> int:
        """获取cookie数量"""
        return len(self.cookies)

cookie_selector = CookieSelector(SESSION_COOKIES)

# 请求头模板
def get_headers(content_type: str = "application/json", cookie: Optional[str] = None) -> dict:
    # 如果未指定cookie，使用轮询选择器获取下一个
    if cookie is None:
        cookie = cookie_selector.get_next()

    if cookie:
        # 打印调试信息 (隐藏中间部分)
        masked_cookie = f"{cookie[:10]}...{cookie[-10:]}" if len(cookie) > 20 else cookie
        print(f"[Debug] 使用 Cookie: {masked_cookie}")

    return {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "no-cache",
        "content-type": content_type,
        "cookie": f"connect.sid={cookie}" if cookie else "",
        "origin": BASE_URL,
        "pragma": "no-cache",
        "referer": f"{BASE_URL}/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }


# ==================== 请求模型 ====================

class VideoCreateRequest(BaseModel):
    """视频创建请求模型"""
    model: str = Field(default="seedance-1-5-pro-251215", description="模型名称")
    prompt: str = Field(..., description="视频描述提示词")
    duration: int = Field(default=5, ge=1, le=10, description="视频时长(秒)")
    radio: str = Field(default="16:9", description="视频比例，如 16:9, 9:16, 1:1")
    image: Optional[str] = Field(default=None, description="图片URL(图生视频时必填)")


class VideoCreateResponse(BaseModel):
    """视频创建响应模型"""
    success: bool
    message: str
    data: Optional[dict] = None


class UploadResponse(BaseModel):
    """上传响应模型"""
    success: bool
    message: str
    url: Optional[str] = None
    data: Optional[dict] = None


class VideoListResponse(BaseModel):
    """视频列表响应模型"""
    success: bool
    data: Optional[list] = None
    message: Optional[str] = None


class VideoStatusResponse(BaseModel):
    """视频状态响应模型"""
    success: bool
    status: Optional[str] = None
    video_url: Optional[str] = None
    data: Optional[dict] = None
    message: Optional[str] = None


# ==================== API 路由 ====================

@app.get("/", tags=["健康检查"])
async def root():
    """API根路径 (无需鉴权)"""
    auth_enabled = len(AUTH_TOKENS) > 0
    return {
        "service": "豆包 Seedance 视频生成 API",
        "version": "1.0.0",
        "cookie_count": cookie_selector.count(),
        "load_balance": "round-robin",
        "auth_enabled": auth_enabled,
        "endpoints": {
            "upload": "POST /api/upload - 上传图片",
            "create_video": "POST /api/video/create - 创建视频",
            "list_videos": "GET /api/videos - 获取视频列表",
            "video_count": "GET /api/stats/video-count - 获取视频统计",
            "video_status": "GET /api/video/{video_id}/status - 查询视频状态",
            "proxy": "GET /proxy/{url} - 视频代理下载"
        }
    }


# ==================== 视频代理接口 ====================

@app.get("/proxy/{target_url:path}", tags=["代理"])
async def proxy_video(target_url: str, request: Request):
    """
    视频代理下载接口

    解决国内网络无法直接访问外网视频URL的问题
    将外网视频通过服务器代理下载

    使用方式:
    - 原始URL: https://ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com/xxx.mp4?...
    - 代理URL: https://your-server.com/proxy/https://ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com/xxx.mp4?...

    参数:
    - target_url: 需要代理的完整URL (URL编码后的)
    """
    # 获取完整的查询参数
    query_string = str(request.query_params)

    # 解码URL
    decoded_url = unquote(target_url)

    # 如果有查询参数，拼接到URL上
    if query_string:
        # 检查decoded_url是否已经包含查询参数
        if "?" in decoded_url:
            full_url = f"{decoded_url}&{query_string}"
        else:
            full_url = f"{decoded_url}?{query_string}"
    else:
        full_url = decoded_url

    # 验证URL格式
    if not full_url.startswith("http://") and not full_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid URL format. URL must start with http:// or https://")

    print(f"[Proxy] 代理请求: {full_url[:100]}...")

    try:
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            # 发起请求获取视频
            response = await client.get(
                full_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                    "Accept-Encoding": "identity",  # 不使用压缩，方便流式传输
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch resource: {response.status_code}"
                )

            # 获取Content-Type
            content_type = response.headers.get("content-type", "application/octet-stream")

            # 获取文件名（如果有的话）
            content_disposition = response.headers.get("content-disposition", "")

            # 构建响应头
            headers = {
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            }

            # 如果有Content-Length，添加到响应头
            if "content-length" in response.headers:
                headers["Content-Length"] = response.headers["content-length"]

            # 如果有Content-Disposition，保留
            if content_disposition:
                headers["Content-Disposition"] = content_disposition

            print(f"[Proxy] 代理成功: {content_type}, {response.headers.get('content-length', 'unknown')} bytes")

            # 返回流式响应
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers=headers
            )

    except httpx.TimeoutException:
        print(f"[Proxy] 代理超时: {full_url[:100]}...")
        raise HTTPException(status_code=504, detail="Proxy request timeout")
    except httpx.RequestError as e:
        print(f"[Proxy] 代理失败: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Proxy request failed: {str(e)}")


@app.post("/api/upload", response_model=UploadResponse, tags=["上传"])
async def upload_image(
    file: UploadFile = File(...),
    token: str = Depends(verify_auth_token)
):
    """
    上传图片

    用于图生视频模式，上传图片后获取图片URL
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        # 读取文件内容
        file_content = await file.read()

        # 构建multipart请求
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            files = {
                "file": (file.filename, file_content, file.content_type or "image/png")
            }

            headers = get_headers()
            # 删除content-type让httpx自动设置multipart边界
            del headers["content-type"]

            response = await client.post(
                f"{BASE_URL}/api/upload",
                files=files,
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(response.url):
                return UploadResponse(
                    success=False,
                    message="上传失败: Session 已过期或无效，请更新 SESSION_COOKIE",
                    data={"error": "Redirected to login page", "url": str(response.url)}
                )

            if response.status_code == 200:
                result = response.json()
                # 兼容 {ok: true, url: "..."} 格式
                is_success = result.get("ok") or result.get("success")
                image_url = result.get("url")

                if is_success and image_url:
                    return UploadResponse(
                        success=True,
                        message="上传成功",
                        url=image_url,
                        data=result
                    )
                else:
                    return UploadResponse(
                        success=False,
                        message=result.get("message") or "上传失败",
                        data=result
                    )
            else:
                return UploadResponse(
                    success=False,
                    message=f"上传失败: {response.status_code}",
                    data={"error": response.text}
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传出错: {str(e)}")


@app.post("/api/video/create", response_model=VideoCreateResponse, tags=["视频生成"])
async def create_video(
    request: VideoCreateRequest,
    token: str = Depends(verify_auth_token)
):
    """
    创建视频

    支持两种模式:
    - 文生视频: 仅提供prompt，不提供image
    - 图生视频: 同时提供prompt和image(图片URL)

    参数:
    - model: 模型名称，默认 seedance-1-5-pro-251215
    - prompt: 视频描述提示词
    - duration: 视频时长(秒)，默认5秒
    - radio: 视频比例，如 16:9, 9:16, 1:1
    - image: 图片URL(图生视频时必填)
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        # 构建请求体
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "duration": request.duration,
            "radio": request.radio
        }

        # 如果有图片URL，添加到请求体(图生视频模式)
        if request.image:
            payload["image"] = request.image

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            headers = get_headers()
            response = await client.post(
                f"{BASE_URL}/api/video/create",
                json=payload,
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(response.url):
                return VideoCreateResponse(
                    success=False,
                    message="创建失败: Session 已过期或无效，请更新 SESSION_COOKIE",
                    data={"error": "Redirected to login page", "url": str(response.url)}
                )

            if response.status_code == 200:
                result = response.json()
                mode = "图生视频" if request.image else "文生视频"
                return VideoCreateResponse(
                    success=True,
                    message=f"视频创建任务已提交 ({mode})",
                    data=result
                )
            else:
                return VideoCreateResponse(
                    success=False,
                    message=f"创建失败: {response.status_code}",
                    data={"error": response.text}
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建视频出错: {str(e)}")


@app.get("/api/videos", response_model=VideoListResponse, tags=["视频管理"])
async def list_videos(token: str = Depends(verify_auth_token)):
    """
    获取视频列表

    返回当前账号下的所有视频记录
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = get_headers()
            del headers["content-type"]  # GET请求不需要content-type

            response = await client.get(
                f"{BASE_URL}/api/videos",
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(response.url):
                return VideoListResponse(
                    success=False,
                    message="获取失败: Session 已过期或无效，请更新 SESSION_COOKIE"
                )

            if response.status_code == 200:
                result = response.json()
                # 兼容多种返回格式: {ok, items} 或 {success, data} 或直接数组
                if isinstance(result, list):
                    items = result
                elif result.get("ok"):
                    items = result.get("items", [])
                else:
                    items = result.get("data", [])

                return VideoListResponse(
                    success=True,
                    data=items
                )
            else:
                return VideoListResponse(
                    success=False,
                    message=f"获取失败: {response.status_code}"
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频列表出错: {str(e)}")


@app.get("/api/stats/video-count", tags=["统计"])
async def get_video_count(token: str = Depends(verify_auth_token)):
    """
    获取视频统计

    返回视频总数等统计信息
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = get_headers()
            del headers["content-type"]

            response = await client.get(
                f"{BASE_URL}/api/stats/video-count",
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(response.url):
                return {"success": False, "message": "获取失败: Session 已过期或无效"}

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "message": f"获取失败: {response.status_code}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计出错: {str(e)}")


@app.get("/api/video/{video_id}/status", response_model=VideoStatusResponse, tags=["视频管理"])
async def get_video_status(
    video_id: str,
    token: str = Depends(verify_auth_token)
):
    """
    查询视频生成状态

    根据视频ID查询生成进度和结果
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        # 通过获取视频列表来查找特定视频的状态
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = get_headers()
            del headers["content-type"]

            response = await client.get(
                f"{BASE_URL}/api/videos",
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(response.url):
                return VideoStatusResponse(
                    success=False,
                    message="查询失败: Session 已过期或无效"
                )

            if response.status_code == 200:
                videos = response.json()
                if isinstance(videos, list):
                    for video in videos:
                        if str(video.get("id")) == video_id or video.get("taskId") == video_id:
                            return VideoStatusResponse(
                                success=True,
                                status=video.get("status"),
                                video_url=video.get("videoUrl"),
                                data=video
                            )
                    return VideoStatusResponse(
                        success=False,
                        message="视频未找到"
                    )
                else:
                    return VideoStatusResponse(
                        success=True,
                        data=videos
                    )
            else:
                return VideoStatusResponse(
                    success=False,
                    message=f"查询失败: {response.status_code}"
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询状态出错: {str(e)}")


@app.post("/api/video/create-with-image", response_model=VideoCreateResponse, tags=["视频生成"])
async def create_video_with_image(
    prompt: str,
    file: UploadFile = File(...),
    model: str = "seedance-1-5-pro-251215",
    duration: int = 5,
    radio: str = "16:9",
    token: str = Depends(verify_auth_token)
):
    """
    图生视频一体化接口

    自动完成图片上传并创建视频，适用于图生视频场景

    参数:
    - prompt: 视频描述提示词
    - file: 图片文件
    - model: 模型名称
    - duration: 视频时长(秒)
    - radio: 视频比例
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        # 第一步: 上传图片
        file_content = await file.read()

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            files = {
                "file": (file.filename, file_content, file.content_type or "image/png")
            }

            headers = get_headers()
            del headers["content-type"]

            upload_response = await client.post(
                f"{BASE_URL}/api/upload",
                files=files,
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(upload_response.url):
                return VideoCreateResponse(
                    success=False,
                    message="图片上传失败: Session 已过期或无效，请更新 SESSION_COOKIE"
                )

            if upload_response.status_code != 200:
                return VideoCreateResponse(
                    success=False,
                    message=f"图片上传失败: {upload_response.status_code}",
                    data={"error": upload_response.text}
                )

            upload_result = upload_response.json()
            image_url = upload_result.get("url")

            if not image_url:
                return VideoCreateResponse(
                    success=False,
                    message="上传成功但未获取到图片URL",
                    data=upload_result
                )

            # 第二步: 创建视频
            payload = {
                "model": model,
                "prompt": prompt,
                "duration": duration,
                "radio": radio,
                "image": image_url
            }

            headers = get_headers()
            create_response = await client.post(
                f"{BASE_URL}/api/video/create",
                json=payload,
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(create_response.url):
                return VideoCreateResponse(
                    success=False,
                    message="视频创建失败: Session 已过期或无效"
                )

            if create_response.status_code == 200:
                result = create_response.json()
                return VideoCreateResponse(
                    success=True,
                    message="图生视频任务已提交",
                    data={
                        "image_url": image_url,
                        "video_task": result
                    }
                )
            else:
                return VideoCreateResponse(
                    success=False,
                    message=f"视频创建失败: {create_response.status_code}",
                    data={"error": create_response.text}
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图生视频出错: {str(e)}")


# ==================== 轮询等待接口 ====================

@app.post("/api/video/create-and-wait", tags=["视频生成"])
async def create_video_and_wait(
    request: VideoCreateRequest,
    max_wait_seconds: int = 300,
    poll_interval: int = 5,
    token: str = Depends(verify_auth_token)
):
    """
    创建视频并等待完成

    创建视频后自动轮询状态，直到视频生成完成或超时

    参数:
    - request: 视频创建请求
    - max_wait_seconds: 最大等待时间(秒)，默认300秒
    - poll_interval: 轮询间隔(秒)，默认5秒
    """
    if cookie_selector.count() == 0:
        raise HTTPException(status_code=401, detail="未配置SESSION_COOKIE")

    try:
        # 创建视频
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "duration": request.duration,
            "radio": request.radio
        }
        if request.image:
            payload["image"] = request.image

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            headers = get_headers()
            response = await client.post(
                f"{BASE_URL}/api/video/create",
                json=payload,
                headers=headers
            )

            # 检查是否被重定向到了登录页
            if "/login" in str(response.url):
                return {
                    "success": False,
                    "message": "创建失败: Session 已过期或无效"
                }

            if response.status_code != 200:
                return {
                    "success": False,
                    "message": f"创建失败: {response.status_code}",
                    "error": response.text
                }

            create_result = response.json()
            task_id = create_result.get("taskId") or create_result.get("id")

            if not task_id:
                return {
                    "success": True,
                    "message": "任务已创建但无法获取任务ID，请手动查询",
                    "data": create_result
                }

            # 轮询等待
            elapsed = 0
            headers = get_headers()
            del headers["content-type"]

            while elapsed < max_wait_seconds:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                # 重新获取 headers (因为 cookie 可能在轮询中变化，虽然目前是单次 client)
                current_headers = get_headers()
                del current_headers["content-type"]

                videos_response = await client.get(
                    f"{BASE_URL}/api/videos",
                    headers=current_headers
                )

                if "/login" in str(videos_response.url):
                    return {
                        "success": False,
                        "message": "轮询失败: Session 已过期或无效",
                        "task_id": task_id
                    }

                if videos_response.status_code == 200:
                    videos = videos_response.json()
                    if isinstance(videos, list):
                        for video in videos:
                            if str(video.get("id")) == str(task_id) or video.get("taskId") == task_id:
                                status = video.get("status")
                                if status == "completed" or status == "success":
                                    return {
                                        "success": True,
                                        "message": "视频生成完成",
                                        "video_url": video.get("videoUrl"),
                                        "data": video
                                    }
                                elif status == "failed" or status == "error":
                                    return {
                                        "success": False,
                                        "message": "视频生成失败",
                                        "data": video
                                    }

            return {
                "success": False,
                "message": f"等待超时({max_wait_seconds}秒)，请稍后手动查询",
                "task_id": task_id
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建视频出错: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
