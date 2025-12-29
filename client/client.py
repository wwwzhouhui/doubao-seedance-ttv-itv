"""
豆包 Seedance 视频生成 API 客户端

使用示例:
    python client.py text2video "一只可爱的猫咪在草地上奔跑"
    python client.py image2video "猫咪跳跃起来" /path/to/cat.png
    python client.py list
    python client.py status <video_id>

鉴权说明:
    如果服务端配置了 AUTH_TOKEN，需要通过 --token 参数或环境变量 AUTH_TOKEN 提供鉴权令牌
"""

import argparse
import json
import sys
import time
import os
import httpx
from pathlib import Path
from datetime import datetime


class DoubaoVideoClient:
    """豆包视频生成客户端"""

    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.getenv("AUTH_TOKEN", "")
        self.client = httpx.Client(timeout=120.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def _get_headers(self) -> dict:
        """获取请求头，包含鉴权信息"""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def upload_image(self, image_path: str) -> dict:
        """
        上传图片

        Args:
            image_path: 图片文件路径

        Returns:
            上传响应，包含图片URL
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        with open(path, "rb") as f:
            files = {"file": (path.name, f, self._get_content_type(path.suffix))}
            response = self.client.post(
                f"{self.base_url}/api/upload",
                files=files,
                headers=self._get_headers()
            )

        return response.json()

    def create_video_text2video(
        self,
        prompt: str,
        model: str = "seedance-1-5-pro-251215",
        duration: int = 5,
        radio: str = "16:9"
    ) -> dict:
        """
        文生视频

        Args:
            prompt: 视频描述提示词
            model: 模型名称
            duration: 视频时长(秒)
            radio: 视频比例

        Returns:
            创建响应
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "radio": radio
        }

        response = self.client.post(
            f"{self.base_url}/api/video/create",
            json=payload,
            headers=self._get_headers()
        )

        return response.json()

    def create_video_image2video(
        self,
        prompt: str,
        image_path: str,
        model: str = "seedance-1-5-pro-251215",
        duration: int = 5,
        radio: str = "16:9"
    ) -> dict:
        """
        图生视频 (先上传图片再创建视频)

        Args:
            prompt: 视频描述提示词
            image_path: 图片文件路径
            model: 模型名称
            duration: 视频时长(秒)
            radio: 视频比例

        Returns:
            创建响应
        """
        # 先上传图片
        print("正在上传图片...")
        upload_result = self.upload_image(image_path)

        if not upload_result.get("success"):
            return upload_result

        image_url = upload_result.get("url")
        if not image_url:
            return {"success": False, "message": "上传成功但未获取到图片URL"}

        print(f"图片上传成功: {image_url}")

        # 创建视频
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "radio": radio,
            "image": image_url
        }

        response = self.client.post(
            f"{self.base_url}/api/video/create",
            json=payload,
            headers=self._get_headers()
        )

        result = response.json()
        result["image_url"] = image_url
        return result

    def create_video_with_image_url(
        self,
        prompt: str,
        image_url: str,
        model: str = "seedance-1-5-pro-251215",
        duration: int = 5,
        radio: str = "16:9"
    ) -> dict:
        """
        图生视频 (使用已有图片URL)

        Args:
            prompt: 视频描述提示词
            image_url: 图片URL
            model: 模型名称
            duration: 视频时长(秒)
            radio: 视频比例

        Returns:
            创建响应
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "radio": radio,
            "image": image_url
        }

        response = self.client.post(
            f"{self.base_url}/api/video/create",
            json=payload,
            headers=self._get_headers()
        )

        return response.json()

    def list_videos(self) -> dict:
        """
        获取视频列表

        Returns:
            视频列表响应
        """
        response = self.client.get(
            f"{self.base_url}/api/videos",
            headers=self._get_headers()
        )
        return response.json()

    def get_video_status(self, video_id: str) -> dict:
        """
        查询视频状态

        Args:
            video_id: 视频ID

        Returns:
            视频状态响应
        """
        response = self.client.get(
            f"{self.base_url}/api/video/{video_id}/status",
            headers=self._get_headers()
        )
        return response.json()

    def get_video_count(self) -> dict:
        """
        获取视频统计

        Returns:
            统计响应
        """
        response = self.client.get(
            f"{self.base_url}/api/stats/video-count",
            headers=self._get_headers()
        )
        return response.json()

    def find_video_by_task_id(self, task_id: str) -> dict:
        """
        根据task_id从视频列表中查找视频

        Args:
            task_id: 任务ID

        Returns:
            视频信息或None
        """
        result = self.list_videos()
        if not result.get("success"):
            return None

        videos = result.get("data", [])
        if not isinstance(videos, list):
            return None

        # 提取核心task_id（去掉 ::model 后缀）
        core_task_id = task_id.split("::")[0] if "::" in task_id else task_id

        for video in videos:
            # 匹配 task_id 或 id
            vid_task_id = video.get("taskId") or video.get("task_id") or ""
            vid_id = str(video.get("id", ""))

            # 精确匹配
            if task_id == vid_task_id or task_id == vid_id:
                return video

            # 核心ID匹配（去掉后缀）
            if core_task_id == vid_task_id or core_task_id == vid_id:
                return video

            # 部分匹配（task_id可能包含额外信息）
            if vid_task_id and core_task_id in vid_task_id:
                return video
            if core_task_id and vid_task_id and vid_task_id in core_task_id:
                return video

        return None

    def wait_for_video(
        self,
        task_id: str,
        max_wait_seconds: int = 600,
        poll_interval: int = 10,
        show_progress: bool = True
    ) -> dict:
        """
        等待视频生成完成

        Args:
            task_id: 任务ID
            max_wait_seconds: 最大等待时间(秒)
            poll_interval: 轮询间隔(秒)
            show_progress: 是否显示进度

        Returns:
            视频结果
        """
        start_time = time.time()
        elapsed = 0

        if show_progress:
            print(f"任务ID: {task_id}")
            print(f"开始轮询等待视频生成完成 (最长等待 {max_wait_seconds} 秒)...")

        while elapsed < max_wait_seconds:
            video = self.find_video_by_task_id(task_id)

            if video:
                status = video.get("status", "").lower()
                # 兼容多种URL字段名
                video_url = video.get("url") or video.get("videoUrl") or video.get("video_url")

                if show_progress:
                    elapsed = int(time.time() - start_time)
                    progress_char = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                    idx = int(elapsed / poll_interval) % len(progress_char)
                    print(f"\r{progress_char[idx]} 状态: {status} | 已等待: {elapsed}秒", end="", flush=True)

                # 检查完成状态
                if status in ["completed", "success", "done", "finished", "succeeded"]:
                    if show_progress:
                        print(f"\n视频生成完成!")
                    return {
                        "success": True,
                        "status": status,
                        "video_url": video_url,
                        "task_id": task_id,
                        "data": video
                    }

                # 检查失败状态
                if status in ["failed", "error", "failure"]:
                    if show_progress:
                        print(f"\n视频生成失败!")
                    return {
                        "success": False,
                        "status": status,
                        "message": video.get("error") or video.get("message") or "视频生成失败",
                        "task_id": task_id,
                        "data": video
                    }

            time.sleep(poll_interval)
            elapsed = time.time() - start_time

        if show_progress:
            print(f"\n等待超时!")

        return {
            "success": False,
            "status": "timeout",
            "message": f"等待超时({max_wait_seconds}秒)，请稍后使用 'status {task_id}' 命令查询",
            "task_id": task_id
        }

    def create_and_wait(
        self,
        prompt: str,
        image_path: str = None,
        image_url: str = None,
        model: str = "seedance-1-5-pro-251215",
        duration: int = 5,
        radio: str = "16:9",
        max_wait_seconds: int = 600,
        poll_interval: int = 10,
        show_progress: bool = True
    ) -> dict:
        """
        创建视频并等待完成

        Args:
            prompt: 视频描述提示词
            image_path: 图片文件路径 (图生视频)
            image_url: 图片URL (图生视频)
            model: 模型名称
            duration: 视频时长(秒)
            radio: 视频比例
            max_wait_seconds: 最大等待时间(秒)
            poll_interval: 轮询间隔(秒)
            show_progress: 是否显示进度

        Returns:
            最终视频结果
        """
        # 确定图片URL
        final_image_url = image_url
        if image_path and not image_url:
            if show_progress:
                print("正在上传图片...")
            upload_result = self.upload_image(image_path)
            if not upload_result.get("success"):
                return upload_result
            final_image_url = upload_result.get("url")
            if show_progress:
                print(f"图片上传成功: {final_image_url}")

        # 创建视频
        if show_progress:
            mode = "图生视频" if final_image_url else "文生视频"
            print(f"正在提交{mode}任务...")

        if final_image_url:
            create_result = self.create_video_with_image_url(
                prompt=prompt,
                image_url=final_image_url,
                model=model,
                duration=duration,
                radio=radio
            )
        else:
            create_result = self.create_video_text2video(
                prompt=prompt,
                model=model,
                duration=duration,
                radio=radio
            )

        if not create_result.get("success"):
            return create_result

        # 提取task_id
        data = create_result.get("data", {})
        task = data.get("task", {})
        task_id = task.get("task_id") or data.get("taskId") or data.get("task_id") or data.get("id")

        if not task_id:
            return {
                "success": False,
                "message": "创建成功但无法获取任务ID",
                "data": create_result
            }

        if show_progress:
            print(f"任务创建成功!")

        # 等待完成
        return self.wait_for_video(
            task_id=task_id,
            max_wait_seconds=max_wait_seconds,
            poll_interval=poll_interval,
            show_progress=show_progress
        )

    def download_video(self, video_url: str, output_path: str = None) -> str:
        """
        下载视频到本地

        Args:
            video_url: 视频URL
            output_path: 输出路径，不指定则自动生成

        Returns:
            保存的文件路径
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"video_{timestamp}.mp4"

        print(f"正在下载视频: {video_url}")

        with httpx.Client(timeout=300.0, follow_redirects=True) as download_client:
            response = download_client.get(video_url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        print(f"视频已保存到: {output_path}")
        return output_path

    def _get_content_type(self, suffix: str) -> str:
        """获取文件MIME类型"""
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp"
        }
        return content_types.get(suffix.lower(), "application/octet-stream")


def main():
    parser = argparse.ArgumentParser(description="豆包 Seedance 视频生成客户端")
    parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="服务器地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="鉴权令牌 (也可通过环境变量 AUTH_TOKEN 设置)"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 文生视频
    t2v_parser = subparsers.add_parser("text2video", aliases=["t2v"], help="文生视频")
    t2v_parser.add_argument("prompt", help="视频描述提示词")
    t2v_parser.add_argument("--model", default="seedance-1-5-pro-251215", help="模型名称")
    t2v_parser.add_argument("--duration", type=int, default=5, help="视频时长(秒)")
    t2v_parser.add_argument("--radio", default="16:9", help="视频比例")
    t2v_parser.add_argument("--no-wait", action="store_true", help="不等待视频生成完成")
    t2v_parser.add_argument("--timeout", type=int, default=600, help="最大等待时间(秒)，默认600")
    t2v_parser.add_argument("--interval", type=int, default=10, help="轮询间隔(秒)，默认10")
    t2v_parser.add_argument("--download", "-d", action="store_true", help="下载视频到本地")
    t2v_parser.add_argument("--output", "-o", help="输出文件路径")

    # 图生视频
    i2v_parser = subparsers.add_parser("image2video", aliases=["i2v"], help="图生视频")
    i2v_parser.add_argument("prompt", help="视频描述提示词")
    i2v_parser.add_argument("image", help="图片文件路径或URL")
    i2v_parser.add_argument("--model", default="seedance-1-5-pro-251215", help="模型名称")
    i2v_parser.add_argument("--duration", type=int, default=5, help="视频时长(秒)")
    i2v_parser.add_argument("--radio", default="16:9", help="视频比例")
    i2v_parser.add_argument("--no-wait", action="store_true", help="不等待视频生成完成")
    i2v_parser.add_argument("--timeout", type=int, default=600, help="最大等待时间(秒)，默认600")
    i2v_parser.add_argument("--interval", type=int, default=10, help="轮询间隔(秒)，默认10")
    i2v_parser.add_argument("--download", "-d", action="store_true", help="下载视频到本地")
    i2v_parser.add_argument("--output", "-o", help="输出文件路径")

    # 上传图片
    upload_parser = subparsers.add_parser("upload", help="上传图片")
    upload_parser.add_argument("image", help="图片文件路径")

    # 视频列表
    subparsers.add_parser("list", help="获取视频列表")

    # 视频状态
    status_parser = subparsers.add_parser("status", help="查询视频状态")
    status_parser.add_argument("video_id", help="视频ID或任务ID")

    # 等待视频
    wait_parser = subparsers.add_parser("wait", help="等待视频生成完成")
    wait_parser.add_argument("task_id", help="任务ID")
    wait_parser.add_argument("--timeout", type=int, default=600, help="最大等待时间(秒)")
    wait_parser.add_argument("--interval", type=int, default=10, help="轮询间隔(秒)")
    wait_parser.add_argument("--download", "-d", action="store_true", help="下载视频到本地")
    wait_parser.add_argument("--output", "-o", help="输出文件路径")

    # 下载视频
    download_parser = subparsers.add_parser("download", help="下载视频")
    download_parser.add_argument("url", help="视频URL")
    download_parser.add_argument("--output", "-o", help="输出文件路径")

    # 视频统计
    subparsers.add_parser("count", help="获取视频统计")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    with DoubaoVideoClient(args.server, auth_token=args.token) as client:
        if args.command in ["text2video", "t2v"]:
            print(f"正在创建文生视频: {args.prompt}")

            if args.no_wait:
                # 不等待，直接返回
                result = client.create_video_text2video(
                    prompt=args.prompt,
                    model=args.model,
                    duration=args.duration,
                    radio=args.radio
                )
                print_result(result)
            else:
                # 等待完成
                result = client.create_and_wait(
                    prompt=args.prompt,
                    model=args.model,
                    duration=args.duration,
                    radio=args.radio,
                    max_wait_seconds=args.timeout,
                    poll_interval=args.interval
                )
                print_result(result)

                # 下载视频
                if result.get("success") and (args.download or args.output):
                    video_url = result.get("video_url")
                    if video_url:
                        client.download_video(video_url, args.output)

        elif args.command in ["image2video", "i2v"]:
            is_url = args.image.startswith("http://") or args.image.startswith("https://")
            print(f"正在创建图生视频: {args.prompt}")

            if args.no_wait:
                # 不等待，直接返回
                if is_url:
                    result = client.create_video_with_image_url(
                        prompt=args.prompt,
                        image_url=args.image,
                        model=args.model,
                        duration=args.duration,
                        radio=args.radio
                    )
                else:
                    result = client.create_video_image2video(
                        prompt=args.prompt,
                        image_path=args.image,
                        model=args.model,
                        duration=args.duration,
                        radio=args.radio
                    )
                print_result(result)
            else:
                # 等待完成
                if is_url:
                    result = client.create_and_wait(
                        prompt=args.prompt,
                        image_url=args.image,
                        model=args.model,
                        duration=args.duration,
                        radio=args.radio,
                        max_wait_seconds=args.timeout,
                        poll_interval=args.interval
                    )
                else:
                    result = client.create_and_wait(
                        prompt=args.prompt,
                        image_path=args.image,
                        model=args.model,
                        duration=args.duration,
                        radio=args.radio,
                        max_wait_seconds=args.timeout,
                        poll_interval=args.interval
                    )
                print_result(result)

                # 下载视频
                if result.get("success") and (args.download or args.output):
                    video_url = result.get("video_url")
                    if video_url:
                        client.download_video(video_url, args.output)

        elif args.command == "upload":
            print(f"正在上传图片: {args.image}")
            result = client.upload_image(args.image)
            print_result(result)

        elif args.command == "list":
            print("正在获取视频列表...")
            result = client.list_videos()
            print_result(result)

        elif args.command == "status":
            print(f"正在查询视频状态: {args.video_id}")
            video = client.find_video_by_task_id(args.video_id)
            if video:
                video_url = video.get("url") or video.get("videoUrl") or video.get("video_url")
                print_result({
                    "success": True,
                    "status": video.get("status"),
                    "video_url": video_url,
                    "data": video
                })
            else:
                # 尝试直接查询
                result = client.get_video_status(args.video_id)
                print_result(result)

        elif args.command == "wait":
            print(f"等待视频生成完成: {args.task_id}")
            result = client.wait_for_video(
                task_id=args.task_id,
                max_wait_seconds=args.timeout,
                poll_interval=args.interval
            )
            print_result(result)

            # 下载视频
            if result.get("success") and (args.download or args.output):
                video_url = result.get("video_url")
                if video_url:
                    client.download_video(video_url, args.output)

        elif args.command == "download":
            client.download_video(args.url, args.output)

        elif args.command == "count":
            print("正在获取视频统计...")
            result = client.get_video_count()
            print_result(result)


def print_result(result: dict):
    """格式化打印结果"""
    print("\n" + "=" * 50)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 50)

    # 额外输出关键信息
    if result.get("success"):
        video_url = result.get("video_url")
        if video_url:
            print(f"\n视频URL: {video_url}")
    else:
        message = result.get("message")
        if message:
            print(f"\n错误信息: {message}")


if __name__ == "__main__":
    main()
