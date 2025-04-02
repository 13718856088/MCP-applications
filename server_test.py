import os
import json
import logging
from datetime import datetime
from collections.abc import Sequence
from typing import Any, Optional
from openai import OpenAI

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
logger = logging.getLogger("deepseek-sse-server")

# API 配置
API_KEY = "YOUR API KEY FOR DEEPSEEK"
API_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"

# 创建可重用参数
http_headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


async def query_deepseek(prompt: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """向 DeepSeek API 发送查询请求"""
    try:
        # 创建 OpenAI 客户端
        client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

        # 调用 API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )

        # 处理响应
        return {
            "model": response.model,
            "response": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        raise RuntimeError(f"DeepSeek API error: {str(e)}")


def create_server_app():
    """创建 MCP 服务器应用"""
    app = Server("deepseek-sse-server")

    @app.list_resources()
    async def list_resources() -> list[Resource]:
        """列出可用的 DeepSeek 资源"""
        uri = AnyUrl(f"deepseek://{DEFAULT_MODEL}/query")
        return [
            Resource(
                uri=uri,
                name=f"DeepSeek {DEFAULT_MODEL} API",
                mimeType="application/json",
                description="DeepSeek AI model query endpoint"
            )
        ]

    @app.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        """读取 DeepSeek 模型的信息"""
        model = DEFAULT_MODEL
        if str(uri).startswith("deepseek://") and str(uri).endswith("/query"):
            model = str(uri).split("/")[-2]
        else:
            raise ValueError(f"Unknown resource: {uri}")

        model_info = {
            "model": model,
            "description": "DeepSeek AI language model",
            "capabilities": ["text generation", "question answering", "code generation"],
            "timestamp": datetime.now().isoformat()
        }

        return json.dumps(model_info, indent=2)

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """列出可用的 DeepSeek 工具"""
        return [
            Tool(
                name="ask_deepseek",
                description="Ask a question to DeepSeek AI",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The question or prompt to send to DeepSeek"
                        },
                        "model": {
                            "type": "string",
                            "description": "DeepSeek model to use (optional)",
                            "default": DEFAULT_MODEL
                        }
                    },
                    "required": ["prompt"]
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """处理 DeepSeek 查询的工具调用"""
        if name != "ask_deepseek":
            raise ValueError(f"Unknown tool: {name}")

        if not isinstance(arguments, dict) or "prompt" not in arguments:
            raise ValueError("Invalid arguments: 'prompt' is required")

        prompt = arguments["prompt"]
        model = arguments.get("model", DEFAULT_MODEL)

        try:
            result = await query_deepseek(prompt, model)

            return [
                TextContent(
                    type="text",
                    text=result["response"]
                )
            ]
        except httpx.HTTPError as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise RuntimeError(f"DeepSeek API error: {str(e)}")

    return app


def main(port: int = 8000):
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
    print(f"启动 DeepSeek SSE 服务器在端口 {port}...")
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DeepSeek SSE Server")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    args = parser.parse_args()

    main(args.port)