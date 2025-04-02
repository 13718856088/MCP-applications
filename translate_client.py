import os
import json
import asyncio
from typing import Any, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Resource, Tool, TextContent


async def main(server_url: str):
    try:
        # 使用 sse_client 连接到服务器
        print(f"正在连接到 Lingva 翻译 SSE 服务器: {server_url}...")

        async with sse_client(server_url) as streams:
            # 创建会话
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()

                print("已连接到 Lingva 翻译 SSE 服务器")

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

                # 获取支持的语言
                print("\n正在获取支持的语言...")
                try:
                    resource_uri = resources[0].uri if resources else None
                    if resource_uri:
                        languages_info = await session.read_resource(resource_uri)
                        languages_data = json.loads(languages_info)
                        if "supported_languages" in languages_data:
                            languages = languages_data["supported_languages"]
                            print("支持的语言:")
                            for lang in languages:
                                if isinstance(lang, dict) and "code" in lang and "name" in lang:
                                    print(f"  {lang['code']} - {lang['name']}")
                                else:
                                    print(f"  {lang}")
                        else:
                            print("无法获取支持的语言列表")
                    else:
                        print("无法获取支持的语言列表")
                except Exception as e:
                    print(f"获取语言列表失败: {str(e)}")

                # 交互式翻译文本
                while True:
                    print("\n" + "=" * 50)
                    text = input("请输入要翻译的文本 (输入 'exit' 退出): ")

                    if text.lower() == 'exit':
                        break

                    source_lang = input("请输入源语言代码 (默认 auto): ") or "auto"
                    target_lang = input("请输入目标语言代码 (默认 zh): ") or "zh"

                    print("\n正在翻译...")

                    # 调用工具
                    result = await session.call_tool("translate_text", {
                        "text": text,
                        "source_lang": source_lang,
                        "target_lang": target_lang
                    })

                    print("\n翻译结果:")
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

    parser = argparse.ArgumentParser(description="Lingva 翻译 SSE 客户端")
    parser.add_argument("--server", type=str, default="http://localhost:8002/sse",
                        help="SSE 服务器 URL")
    args = parser.parse_args()

    asyncio.run(main(args.server))