import os
import json
import logging
from datetime import datetime
from collections.abc import Sequence
from typing import Any, Optional, List

import httpx
import asyncio
import uvicorn
import anyio
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import AnyUrl

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lingva-translate-server")

# API 配置
LINGVA_API_URL = os.getenv("LINGVA_API_URL", "https://lingva.garudalinux.org/api/v1")
# 备选 API 端点列表
LINGVA_API_ALTERNATIVES = [
    "https://lingva.garudalinux.org/api/v1",
    "https://lingva.pussthecat.org/api/v1",
    "https://translate.plausibility.cloud/api/v1",
    "https://translate.dr460nf1r3.org/api/v1"
]


async def get_available_languages() -> List[dict]:
    """获取 Lingva Translate 支持的语言列表"""
    global LINGVA_API_URL
    errors = []

    # 首先尝试主 API 端点
    try:
        url = f"{LINGVA_API_URL}/languages"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        errors.append(f"Primary API error: {str(e)}")
        logger.warning(f"Primary API failed for languages, trying alternatives: {str(e)}")

    # 如果主 API 端点失败，尝试备选端点
    for alt_api_url in LINGVA_API_ALTERNATIVES:
        if alt_api_url == LINGVA_API_URL:
            continue  # 跳过已经尝试过的主 API 端点

        try:
            url = f"{alt_api_url}/languages"

            logger.info(f"Trying alternative API for languages: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()

                # 更新主 API 端点为成功的备选端点
                LINGVA_API_URL = alt_api_url
                logger.info(f"Updated primary API endpoint to: {LINGVA_API_URL}")

                return response.json()
        except Exception as e:
            errors.append(f"Alternative API {alt_api_url} error: {str(e)}")
            logger.warning(f"Alternative API failed for languages: {str(e)}")

    # 如果所有 API 端点都失败，返回一个基本的语言列表
    logger.error(f"All Lingva API endpoints failed for languages: {errors}")

    # 返回一个基本的语言列表，以便服务仍然可以运行
    return [
        {"code": "auto", "name": "Detect Language"},
        {"code": "en", "name": "English"},
        {"code": "zh", "name": "Chinese"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "ru", "name": "Russian"}
    ]


async def translate_text(text: str, source_lang: str, target_lang: str) -> dict[str, Any]:
    """向 Lingva Translate API 发送翻译请求"""
    global LINGVA_API_URL
    # 尝试所有可能的 API 端点
    errors = []

    # URL 编码文本
    import urllib.parse
    encoded_text = urllib.parse.quote(text)

    # 首先尝试主 API 端点
    try:
        # 构建 API URL
        url = f"{LINGVA_API_URL}/{source_lang}/{target_lang}/{encoded_text}"

        logger.info(f"Sending translation request to: {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)

            # 记录响应状态
            logger.info(f"Response status: {response.status_code}")

            response.raise_for_status()
            data = response.json()

            # 格式化翻译结果
            translation_info = {
                "original_text": text,
                "translated_text": data["translation"],
                "source_language": source_lang,
                "target_language": target_lang,
                "timestamp": datetime.now().isoformat()
            }

            return translation_info
    except Exception as e:
        errors.append(f"Primary API error: {str(e)}")
        logger.warning(f"Primary API failed, trying alternatives: {str(e)}")

    # 如果主 API 端点失败，尝试备选端点
    for alt_api_url in LINGVA_API_ALTERNATIVES:
        if alt_api_url == LINGVA_API_URL:
            continue  # 跳过已经尝试过的主 API 端点

        try:
            url = f"{alt_api_url}/{source_lang}/{target_lang}/{encoded_text}"

            logger.info(f"Trying alternative API: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                # 格式化翻译结果
                translation_info = {
                    "original_text": text,
                    "translated_text": data["translation"],
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "timestamp": datetime.now().isoformat(),
                    "api_used": alt_api_url
                }

                # 更新主 API 端点为成功的备选端点
                LINGVA_API_URL = alt_api_url
                logger.info(f"Updated primary API endpoint to: {LINGVA_API_URL}")

                return translation_info
        except Exception as e:
            errors.append(f"Alternative API {alt_api_url} error: {str(e)}")
            logger.warning(f"Alternative API failed: {str(e)}")

    # 如果所有 API 端点都失败，抛出异常
    error_message = "\n".join(errors)
    logger.error(f"All Lingva API endpoints failed: {error_message}")
    raise RuntimeError(f"All Lingva API endpoints failed: {error_message}")


def create_server_app():
    """创建 MCP 服务器应用"""
    app = Server("lingva-translate-server")

    @app.list_resources()
    async def list_resources() -> list[Resource]:
        """列出可用的翻译资源"""
        uri = AnyUrl(f"translate://lingva/query")
        return [
            Resource(
                uri=uri,
                name="Lingva Translate API",
                mimeType="application/json",
                description="Lingva Translate API for text translation"
            )
        ]

    @app.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        """读取翻译服务的信息"""
        if str(uri).startswith("translate://") and str(uri).endswith("/query"):
            try:
                languages = await get_available_languages()

                service_info = {
                    "service": "Lingva Translate",
                    "description": "Free and Open Source Translation API (Google Translate frontend)",
                    "supported_languages": languages,
                    "active_api_endpoint": LINGVA_API_URL,
                    "alternative_endpoints": LINGVA_API_ALTERNATIVES,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(service_info, indent=2)
            except Exception as e:
                logger.error(f"Error fetching languages: {str(e)}")
                service_info = {
                    "service": "Lingva Translate",
                    "description": "Free and Open Source Translation API",
                    "error": f"Could not fetch supported languages: {str(e)}",
                    "active_api_endpoint": LINGVA_API_URL,
                    "alternative_endpoints": LINGVA_API_ALTERNATIVES,
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(service_info, indent=2)
        else:
            raise ValueError(f"Unknown resource: {uri}")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """列出可用的翻译工具"""
        return [
            Tool(
                name="translate_text",
                description="Translate text between languages using Lingva Translate",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to translate"
                        },
                        "source_lang": {
                            "type": "string",
                            "description": "Source language code (e.g., 'en', 'zh', 'auto' for auto-detection)",
                            "default": "auto"
                        },
                        "target_lang": {
                            "type": "string",
                            "description": "Target language code (e.g., 'en', 'zh')",
                            "default": "zh"
                        }
                    },
                    "required": ["text", "target_lang"]
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """处理翻译的工具调用"""
        if name != "translate_text":
            raise ValueError(f"Unknown tool: {name}")

        if not isinstance(arguments, dict) or "text" not in arguments or "target_lang" not in arguments:
            raise ValueError("Invalid arguments: 'text' and 'target_lang' are required")

        text = arguments["text"]
        source_lang = arguments.get("source_lang", "auto")
        target_lang = arguments["target_lang"]

        try:
            result = await translate_text(text, source_lang, target_lang)

            # 构建友好的响应文本
            response_text = f"原文 ({result['source_language']}): {result['original_text']}\n\n"
            response_text += f"译文 ({result['target_language']}): {result['translated_text']}\n"
            if "api_used" in result:
                response_text += f"使用的 API: {result['api_used']}\n"
            response_text += f"翻译时间: {result['timestamp']}"

            return [
                TextContent(
                    type="text",
                    text=response_text
                )
            ]
        except Exception as e:
            logger.error(f"Translation API error: {str(e)}")
            raise RuntimeError(f"Translation API error: {str(e)}")

    return app


def main(port: int = 8002):
    """主函数，启动 SSE 服务器"""
    app = create_server_app()
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        """处理 SSE 连接"""
        async with sse.connect_sse(
                request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    # 创建 Starlette 应用
    starlette_app = Starlette(
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    # 启动服务器
    print(f"启动 Lingva 翻译 SSE 服务器在端口 {port}...")
    print(f"当前使用的 API 端点: {LINGVA_API_URL}")
    print(f"备选 API 端点: {', '.join(LINGVA_API_ALTERNATIVES)}")
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lingva 翻译 SSE 服务器")
    parser.add_argument("--port", type=int, default=8002, help="服务器端口")
    parser.add_argument("--api-url", type=str, help="Lingva API URL (默认: https://lingva.garudalinux.org/api/v1)")
    parser.add_argument("--add-api", type=str, action="append", help="添加备选 API 端点")
    args = parser.parse_args()

    if args.api_url:
        LINGVA_API_URL = args.api_url

    if args.add_api:
        for api in args.add_api:
            if api not in LINGVA_API_ALTERNATIVES:
                LINGVA_API_ALTERNATIVES.append(api)

    main(args.port)