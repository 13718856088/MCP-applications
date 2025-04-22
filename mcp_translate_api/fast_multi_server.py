import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lingva-translate-server")

# 服务API配置
LINGVA_API_URL = os.getenv("LINGVA_API_URL", "http://localhost:8001/api")
TIME_API_URL = os.getenv("TIME_API_URL", "http://localhost:8002/api")

# 创建FastMCP实例
mcp = FastMCP("lingva-translate-server")


@mcp.tool()
async def translate_text(text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
    """将文本翻译成指定语言

    Args:
        text: 要翻译的文本
        source_lang: 源语言代码 (例如: 'en', 'zh', 'auto' 表示自动检测)
        target_lang: 目标语言代码 (例如: 'en', 'zh')

    Returns:
        包含翻译结果的字典
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LINGVA_API_URL}/translate",
                params={
                    "text": text,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                return f"翻译失败: {data.get('detail', '翻译失败')}"

            result = data.get("result", {})
            response_text = (
                f"原文 ({result.get('source_language')}): {result.get('original_text')}\n"
                f"译文 ({result.get('target_language')}): {result.get('translated_text')}\n"
                f"翻译时间: {result.get('timestamp')}"
            )
            return response_text
    except httpx.RequestError as e:
        logger.error(f"翻译API请求错误: {str(e)}")
        return f"翻译API请求错误: {str(e)}"


@mcp.tool()
async def get_current_time(timezone: str = "UTC", format: str = "%Y-%m-%d %H:%M:%S") -> Dict[str, Any]:
    """获取当前日期和时间，支持指定时区

    Args:
        timezone: 时区名称 (例如: 'Asia/Shanghai', 'America/New_York', 'UTC')
        format: 日期时间格式 (例如: '%Y-%m-%d %H:%M:%S', '%Y年%m月%d日 %H时%M分%S秒')

    Returns:
        包含时间信息的字典
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TIME_API_URL}/time",
                params={
                    "timezone": timezone,
                    "format": format
                }
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                return {"error": data.get("detail", "获取时间失败")}

            result = data.get("result", {})
            return {
                "current_time": result.get("current_time"),
                "timezone": result.get("timezone"),
                "format": result.get("format"),
                "utc_time": result.get("utc_time"),
                "timestamp": result.get("timestamp")
            }
    except httpx.RequestError as e:
        logger.error(f"时间API请求错误: {str(e)}")
        return {"error": f"时间API请求错误: {str(e)}"}


@mcp.resource("translate://lingva/query")
async def get_translation_info() -> Dict[str, Any]:
    """获取翻译服务信息"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LINGVA_API_URL}/info")
            response.raise_for_status()
            data = response.json()

            # 获取语言列表
            languages_response = await client.get(f"{LINGVA_API_URL}/languages")
            languages_response.raise_for_status()
            languages_data = languages_response.json()

            return {
                "service": data.get("service", "Lingva Translate"),
                "description": data.get("description", "Free and Open Source Translation API"),
                "supported_languages": languages_data.get("languages", []),
                "active_api_endpoint": data.get("active_api_endpoint"),
                "alternative_endpoints": data.get("alternative_endpoints", []),
                "timestamp": datetime.now().isoformat()
            }
    except httpx.RequestError as e:
        logger.error(f"获取服务信息失败: {str(e)}")
        return {
            "service": "Lingva Translate",
            "description": "Free and Open Source Translation API",
            "error": f"获取服务信息失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Lingva 翻译服务器 (FastMCP版本)")
    parser.add_argument("--port", type=int, default=8003, help="服务器端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机")
    parser.add_argument("--lingva-api", type=str, help="Lingva API URL (默认: http://localhost:8001/api)")
    parser.add_argument("--time-api", type=str, help="Time API URL (默认: http://localhost:8002/api)")
    args = parser.parse_args()

    if args.lingva_api:
        LINGVA_API_URL = args.lingva_api

    if args.time_api:
        TIME_API_URL = args.time_api

    print(f"启动FastMCP服务 在端口 {args.port}...")
    print(f"连接到翻译服务 API: {LINGVA_API_URL}")
    print(f"连接到时间服务 API: {TIME_API_URL}")

    mcp.run(transport='sse')