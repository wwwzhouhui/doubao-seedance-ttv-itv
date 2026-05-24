"""
豆包 Seedance 视频生成 Gradio 前端界面
支持文生视频和图生视频两种模式

在 Gradio 容器中运行时，会自动启动内置 API 服务 (server/api.py)
内置 API 服务提供视频代理下载功能，解决国内网络无法直接访问外网视频URL的问题
"""

import os
import sys
import time
import tempfile
import subprocess
import threading
import atexit
import httpx
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
ENABLE_INTERNAL_API = os.getenv("ENABLE_INTERNAL_API", "true").lower() == "true"

# API鉴权Token
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")


def get_auth_headers() -> dict:
    """获取包含鉴权信息的请求头"""
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return headers


# 全局变量存储API进程
_api_process = None


def start_api_server():
    """启动内置API服务器"""
    global _api_process

    # 检查api.py是否存在 (支持两种路径: Docker容器和本地开发)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 优先检查同目录下的 api.py (Docker 容器环境)
    api_py_path = os.path.join(base_dir, "api.py")
    api_module = "api:app"

    # 如果同目录下不存在，检查 server/ 子目录 (本地开发环境)
    if not os.path.exists(api_py_path):
        api_py_path = os.path.join(base_dir, "server", "api.py")
        api_module = "server.api:app"

    if not os.path.exists(api_py_path):
        print(f"[API] ❌ api.py not found, skipping internal API server")
        print(f"[API]    Checked paths:")
        print(f"[API]    - {os.path.join(base_dir, 'api.py')}")
        print(f"[API]    - {os.path.join(base_dir, 'server', 'api.py')}")
        return False

    print(f"[API] 📁 Found api.py at: {api_py_path}")
    print(f"[API] 🚀 Starting internal API server on {API_HOST}:{API_PORT}...")

    try:
        # 使用 uvicorn 启动 API 服务
        _api_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                api_module,
                "--host", API_HOST,
                "--port", str(API_PORT),
                "--log-level", "info"
            ],
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # 启动日志输出线程
        def log_output():
            if _api_process and _api_process.stdout:
                for line in _api_process.stdout:
                    print(f"[API] {line.rstrip()}")

        log_thread = threading.Thread(target=log_output, daemon=True)
        log_thread.start()

        # 等待API服务启动
        max_retries = 30
        for i in range(max_retries):
            try:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(f"http://localhost:{API_PORT}/")
                    if response.status_code == 200:
                        print(f"[API] Server started successfully on port {API_PORT}")
                        return True
            except Exception:
                pass
            time.sleep(1)
            if i % 5 == 0:
                print(f"[API] Waiting for server to start... ({i}/{max_retries})")

        print(f"[API] Warning: Server may not have started properly after {max_retries}s")
        return False

    except Exception as e:
        print(f"[API] Failed to start server: {e}")
        return False


def stop_api_server():
    """停止API服务器"""
    global _api_process
    if _api_process:
        print("[API] Stopping internal API server...")
        _api_process.terminate()
        try:
            _api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _api_process.kill()
        _api_process = None
        print("[API] Server stopped")


# 注册退出时清理
atexit.register(stop_api_server)

# 模型选项
MODEL_OPTIONS = [
    ("seedance-1-5-pro-251215 (最新)", "seedance-1-5-pro-251215"),
    ("seedance-1-0-pro-fast (快速)", "seedance-1-0-pro-fast"),
]

# 时长选项
DURATION_OPTIONS = [4, 5, 8, 12]

# 比例选项
RATIO_OPTIONS = [
    ("21:9 (超宽银幕)", "21:9"),
    ("16:9 (横屏·默认)", "16:9"),
    ("4:3 (经典比例)", "4:3"),
    ("1:1 (正方形)", "1:1"),
    ("3:4 (竖屏偏方)", "3:4"),
    ("9:16 (竖屏·抖音/Shorts)", "9:16"),
]


def upload_image(file_path: str) -> dict:
    """上传图片"""
    with httpx.Client(timeout=60.0) as client:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "image/png")}
            response = client.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                headers=get_auth_headers()
            )
            return response.json()


def create_video(prompt: str, model: str, duration: int, ratio: str, image_url: str = None) -> dict:
    """创建视频"""
    payload = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "radio": ratio
    }
    if image_url:
        payload["image"] = image_url

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{API_BASE_URL}/api/video/create",
            json=payload,
            headers=get_auth_headers()
        )
        return response.json()


def get_videos() -> list:
    """获取视频列表"""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{API_BASE_URL}/api/videos",
            headers=get_auth_headers()
        )
        result = response.json()
        if result.get("success"):
            return result.get("data", [])
        return []


def find_video_by_task_id(task_id: str) -> dict:
    """根据task_id从视频列表中查找视频"""
    videos = get_videos()
    if not videos:
        return None

    # 提取核心task_id（去掉 ::model 后缀）
    core_task_id = task_id.split("::")[0] if "::" in task_id else task_id

    for video in videos:
        vid_task_id = video.get("taskId") or video.get("task_id") or ""
        vid_id = str(video.get("id", ""))

        # 精确匹配
        if task_id == vid_task_id or task_id == vid_id:
            return video

        # 核心ID匹配
        if core_task_id == vid_task_id or core_task_id == vid_id:
            return video

        # 部分匹配
        if vid_task_id and core_task_id in vid_task_id:
            return video
        if core_task_id and vid_task_id and vid_task_id in core_task_id:
            return video

    return None


def download_video_to_local(video_url: str) -> str:
    """
    下载视频到本地临时文件
    优先使用内部API代理下载，解决国内网络无法直接访问外网视频URL的问题
    """
    if not video_url:
        return None

    try:
        print(f"[Gradio] 📥 正在下载视频到本地...")
        print(f"[Gradio] 📎 视频远程地址: {video_url}")

        # 检查是否需要使用代理（外网视频域名）
        proxy_domains = [
            "ark-content-generation",
            "tos-ap-southeast",
            "volces.com"
        ]
        use_proxy = any(domain in video_url for domain in proxy_domains)

        if use_proxy:
            # 使用内部API代理URL下载
            download_url = f"{API_BASE_URL}/proxy/{video_url}"
            print(f"[Gradio] 🔄 使用内部API代理下载...")
        else:
            download_url = video_url

        # 使用较长的超时时间，视频文件可能较大
        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            response = client.get(download_url)

            if response.status_code == 200:
                # 获取文件扩展名
                content_type = response.headers.get("content-type", "")
                if "mp4" in content_type or video_url.endswith(".mp4"):
                    suffix = ".mp4"
                elif "webm" in content_type or video_url.endswith(".webm"):
                    suffix = ".webm"
                else:
                    suffix = ".mp4"  # 默认mp4

                # 创建临时文件
                fd, temp_path = tempfile.mkstemp(suffix=suffix)
                with os.fdopen(fd, 'wb') as f:
                    f.write(response.content)

                file_size = len(response.content) / (1024 * 1024)  # MB
                print(f"[Gradio] ✅ 视频下载完成: {temp_path} ({file_size:.2f} MB)")
                return temp_path
            else:
                print(f"[Gradio] ❌ 视频下载失败: HTTP {response.status_code}")
                return None

    except httpx.TimeoutException:
        print(f"[Gradio] ❌ 视频下载超时")
        return None
    except Exception as e:
        print(f"[Gradio] ❌ 视频下载失败: {e}")
        return None


def generate_video(prompt: str, model: str, duration: int, ratio: str, image=None):
    """生成视频主函数 - 包含轮询等待逻辑"""
    if not prompt or not prompt.strip():
        return None, "❌ 请输入视频描述提示词"

    max_wait_seconds = 600  # 最大等待10分钟
    poll_interval = 10  # 每10秒轮询一次

    try:
        # 如果有图片，先上传
        image_url = None
        if image is not None:
            print("[Gradio] 📤 正在上传图片...")
            upload_result = upload_image(image)
            if not upload_result.get("success"):
                return None, f"❌ 图片上传失败: {upload_result.get('message', '未知错误')}"
            image_url = upload_result.get("url")
            if not image_url:
                return None, "❌ 上传成功但未获取到图片URL"

        # 创建视频任务
        mode = "图生视频" if image_url else "文生视频"
        print(f"[Gradio] 🎬 正在提交{mode}任务...")

        create_result = create_video(prompt, model, duration, ratio, image_url)

        if not create_result.get("success"):
            return None, f"❌ 创建任务失败: {create_result.get('message', '未知错误')}"

        # 提取task_id
        task_data = create_result.get("data", {})
        task = task_data.get("task", {})
        task_id = task.get("task_id") or task_data.get("taskId") or task_data.get("task_id") or task_data.get("id")

        if not task_id:
            return None, f"⚠️ 任务已提交({mode})，但无法获取任务ID，请稍后手动查询"

        print(f"[Gradio] ✅ 任务创建成功! 任务ID: {task_id}")

        # 轮询等待视频生成完成
        start_time = time.time()
        elapsed = 0
        progress_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        while elapsed < max_wait_seconds:
            # 查找视频
            video = find_video_by_task_id(task_id)

            if video:
                status = (video.get("status") or "").lower()
                video_url = video.get("url") or video.get("videoUrl") or video.get("video_url")

                # 检查完成状态
                if status in ["completed", "success", "done", "finished", "succeeded"]:
                    print(f"[Gradio] 🎉 视频生成完成!")
                    if video_url:
                        # 下载视频到本地，避免Gradio直接访问外网URL导致DNS解析失败
                        local_path = download_video_to_local(video_url)
                        if local_path:
                            return local_path, f"✅ 视频生成成功! ({mode})\n⏱️ 耗时: {int(elapsed)}秒\n📎 视频URL: {video_url}\n💡 已通过内部API代理下载"
                        else:
                            # 下载失败时返回代理URL供用户手动下载
                            proxy_url = f"{API_BASE_URL}/proxy/{video_url}"
                            return None, f"⚠️ 视频生成完成但下载失败\n📎 原始URL: {video_url}\n🔗 代理URL: {proxy_url}\n请复制代理链接手动下载"
                    else:
                        return None, f"⚠️ 视频生成完成但未获取到URL"

                # 检查失败状态
                if status in ["failed", "error", "failure"]:
                    error_msg = video.get("error") or video.get("message") or "未知错误"
                    return None, f"❌ 视频生成失败: {error_msg}"

            # 更新进度
            elapsed = time.time() - start_time
            idx = int(elapsed / poll_interval) % len(progress_chars)
            print(f"[Gradio] {progress_chars[idx]} 视频生成中... 已等待 {int(elapsed)}秒")

            # 等待下次轮询
            time.sleep(poll_interval)

        # 超时
        return None, f"⏰ 等待超时({max_wait_seconds}秒)，任务ID: {task_id}\n请稍后使用任务ID查询结果"

    except httpx.ConnectError:
        return None, "❌ 无法连接到API服务器，请确保后端服务已启动"
    except Exception as e:
        return None, f"❌ 发生错误: {str(e)}"


# 构建Gradio界面
def create_ui():
    with gr.Blocks(
        title="豆包 Seedance 视频生成"
    ) as demo:

        # 头部
        api_status = "✅ 内置API服务" if ENABLE_INTERNAL_API else "🔗 外部API服务"
        gr.Markdown(f"""
        # 🎬 豆包 Seedance 视频生成
        **新视频模型 seedance-1-5-pro-251215 上线，生成视频带声音，欢迎使用！**

        {api_status}: `{API_BASE_URL}` | 支持视频代理下载
        """)

        # 主布局：左侧输入区域，右侧输出区域
        with gr.Row():
            # 左侧：输入参数区域
            with gr.Column(scale=1):
                # 提示词输入
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="(输入限制1000字符) 描述你想生成的视频内容，例如：夜晚的赛博朋克城市，雨水反射霓虹灯，电影级镜头...",
                    lines=4,
                    max_lines=8
                )
                gr.Markdown("*描述越具体，生成效果越稳定*")

                # 模型选择
                model = gr.Dropdown(
                    label="模型 (model)",
                    choices=[m[0] for m in MODEL_OPTIONS],
                    value=MODEL_OPTIONS[0][0],
                    interactive=True
                )

                # 时长和比例并排
                with gr.Row():
                    # 时长选择
                    with gr.Column(scale=1):
                        duration = gr.Slider(
                            label="时长 (duration)",
                            minimum=4,
                            maximum=12,
                            step=1,
                            value=5,
                            interactive=True
                        )
                        with gr.Row():
                            btn_4s = gr.Button("4s")
                            btn_5s = gr.Button("5s", variant="primary")
                            btn_8s = gr.Button("8s")
                            btn_12s = gr.Button("12s")

                    # 比例选择
                    with gr.Column(scale=1):
                        ratio = gr.Dropdown(
                            label="比例 (radio)",
                            choices=[r[0] for r in RATIO_OPTIONS],
                            value=RATIO_OPTIONS[1][0],
                            interactive=True
                        )

                # 图片上传(可选) - 显示缩略图
                gr.Markdown("### 视频图片 (Optional)")
                image = gr.Image(
                    label="上传参考图片 (图生视频模式)",
                    type="filepath",
                    sources=["upload"],
                    interactive=True,
                    height=200
                )
                gr.Markdown("*当前模型最多支持1张参考图*")

                # 生成按钮
                gr.Markdown("*提交后请耐心等待，视频生成通常需要1-5分钟*")
                generate_btn = gr.Button("🎬 生成视频", variant="primary")

            # 右侧：输出结果区域
            with gr.Column(scale=1):
                gr.Markdown("### 生成结果")
                video_output = gr.Video(
                    label="生成的视频",
                    interactive=False,
                    height=350
                )
                status_output = gr.Textbox(
                    label="状态信息",
                    interactive=False,
                    lines=6
                )

        # 事件绑定
        # 时长快捷按钮
        btn_4s.click(fn=lambda: 4, outputs=duration)
        btn_5s.click(fn=lambda: 5, outputs=duration)
        btn_8s.click(fn=lambda: 8, outputs=duration)
        btn_12s.click(fn=lambda: 12, outputs=duration)

        # 生成视频
        def process_generate(prompt_text, model_text, duration_val, ratio_text, image_file):
            # 转换模型名称
            model_value = next((m[1] for m in MODEL_OPTIONS if m[0] == model_text), MODEL_OPTIONS[0][1])
            # 转换比例名称
            ratio_value = next((r[1] for r in RATIO_OPTIONS if r[0] == ratio_text), RATIO_OPTIONS[1][1])
            return generate_video(prompt_text, model_value, int(duration_val), ratio_value, image_file)

        generate_btn.click(
            fn=process_generate,
            inputs=[prompt, model, duration, ratio, image],
            outputs=[video_output, status_output],
            show_progress=True
        )

    return demo


# 启动内置API服务 (在模块加载时启动，确保Gradio容器也能正常工作)
if ENABLE_INTERNAL_API:
    start_api_server()


if __name__ == "__main__":
    print(f"[Gradio] 🚀 启动 Seedance 视频生成服务")
    print(f"[Gradio] 🔗 API服务地址: {API_BASE_URL}")
    print(f"[Gradio] 📦 内置API状态: {'已启用' if ENABLE_INTERNAL_API else '已禁用'}")
    print(f"[Gradio] 🔑 鉴权状态: {'已配置' if AUTH_TOKEN else '未配置'}")
    print(f"[Gradio] 🌐 视频代理: {API_BASE_URL}/proxy/...")

    demo = create_ui()
    port = int(os.getenv("GRADIO_PORT", "7860"))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True
    )
