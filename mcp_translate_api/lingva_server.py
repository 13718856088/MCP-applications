import os
import logging
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv

# 导入服务类
from services.lingva_service import LingvaService

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lingva-api-server")

# 初始化服务
lingva_service = LingvaService()

# 创建FastAPI应用
app = FastAPI(
    title="Lingva Translate API",
    description="Lingva Translate API服务",
    version="1.0.0"
)

# 定义请求模型
class TranslationRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "zh"

# 定义API路由
@app.get("/api/languages")
async def get_languages():
    """获取支持的语言列表"""
    try:
        languages = await lingva_service.get_available_languages()
        return {
            "success": True,
            "languages": languages,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取语言列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取语言列表失败: {str(e)}")

@app.post("/api/translate")
async def translate(request: TranslationRequest):
    """翻译文本"""
    try:
        result = await lingva_service.translate_text(
            request.text,
            request.source_lang,
            request.target_lang
        )
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"翻译失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"翻译失败: {str(e)}")

@app.get("/api/translate")
async def translate_get(
    text: str,
    source_lang: str = "auto",
    target_lang: str = "zh"
):
    """GET方式翻译文本"""
    try:
        result = await lingva_service.translate_text(
            text,
            source_lang,
            target_lang
        )
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"翻译失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"翻译失败: {str(e)}")

@app.get("/api/info")
async def get_service_info():
    """获取服务信息"""
    try:
        return {
            "service": "Lingva Translate",
            "description": "Free and Open Source Translation API (Google Translate frontend)",
            "active_api_endpoint": lingva_service.primary_api_url,
            "alternative_endpoints": lingva_service.api_alternatives,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取服务信息失败: {str(e)}")
        return {
            "service": "Lingva Translate",
            "description": "Free and Open Source Translation API",
            "error": f"获取服务信息失败: {str(e)}",
            "active_api_endpoint": lingva_service.primary_api_url,
            "alternative_endpoints": lingva_service.api_alternatives,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lingva 翻译 API 服务器")
    parser.add_argument("--port", type=int, default=8001, help="服务器端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机")
    parser.add_argument("--api-url", type=str, help="Lingva API URL (默认: https://lingva.garudalinux.org/api/v1)")
    parser.add_argument("--add-api", type=str, action="append", help="添加备选 API 端点")
    args = parser.parse_args()

    if args.api_url:
        lingva_service.primary_api_url = args.api_url

    if args.add_api:
        for api in args.add_api:
            if api not in lingva_service.api_alternatives:
                lingva_service.api_alternatives.append(api)

    print(f"启动 Lingva 翻译 API 服务器在端口 {args.port}...")
    print(f"当前使用的 API 端点: {lingva_service.primary_api_url}")
    print(f"备选 API 端点: {', '.join(lingva_service.api_alternatives)}")
    uvicorn.run(app, host=args.host, port=args.port)