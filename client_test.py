import os
import json
import asyncio
from typing import Any, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Resource, Tool, TextContent


async def main():
    try:
        # 使用 sse_client 连接到服务器
        server_url = "http://localhost:8000/sse"
        print(f"正在连接到 DeepSeek MCP SSE 服务器: {server_url}...")

        async with sse_client(server_url) as streams:
            # 创建会话
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()

                print("已连接到 DeepSeek MCP SSE 服务器")

                # 获取可用资源
                resources = await session.list_resources()
                print("\n可用资源:")
                for resource in resources:
                    print(resource)

                # 获取可用工具
                tools = await session.list_tools()
                print("\n可用工具:")
                for tool in tools:
                    print(tool)

                # 交互式查询 DeepSeek
                while True:
                    print("\n" + "=" * 50)
                    prompt = input("请输入您的问题 (输入 'exit' 退出): ")

                    if prompt.lower() == 'exit':
                        break

                    print("\n正在向 DeepSeek 发送查询...")

                    # 调用工具
                    result = await session.call_tool("ask_deepseek", {"prompt": prompt})

                    print("\nDeepSeek 回答:")
                    # 处理结果
                    for content in result:
                        if hasattr(content, 'text'):
                            print(content.text)
                        else:
                            print(content)

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理
        print("\n关闭连接并清理资源...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DeepSeek SSE Client")
    parser.add_argument("--server", type=str, default="http://localhost:8000/sse",
                        help="SSE 服务器 URL")
    args = parser.parse_args()

    asyncio.run(main())