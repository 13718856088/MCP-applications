import os
import logging
import urllib.parse
from datetime import datetime
from typing import List, Any, Dict
import httpx

logger = logging.getLogger("lingva-service")

class LingvaService:
    """Lingva翻译服务封装类"""
    
    def __init__(self, primary_api_url=None, api_alternatives=None):
        # 主API端点
        self.primary_api_url = primary_api_url or os.getenv(
            "LINGVA_API_URL", "https://lingva.garudalinux.org/api/v1"
        )
        
        # 备选API端点列表
        self.api_alternatives = api_alternatives or [
            "https://lingva.garudalinux.org/api/v1",
            "https://lingva.pussthecat.org/api/v1",
            "https://translate.plausibility.cloud/api/v1",
            "https://translate.dr460nf1r3.org/api/v1"
        ]
    
    async def get_available_languages(self) -> List[dict]:
        """获取Lingva Translate支持的语言列表"""
        errors = []

        # 首先尝试主API端点
        try:
            url = f"{self.primary_api_url}/languages"

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            errors.append(f"Primary API error: {str(e)}")
            logger.warning(f"Primary API failed for languages, trying alternatives: {str(e)}")

        # 如果主API端点失败，尝试备选端点
        for alt_api_url in self.api_alternatives:
            if alt_api_url == self.primary_api_url:
                continue  # 跳过已经尝试过的主API端点

            try:
                url = f"{alt_api_url}/languages"
                logger.info(f"Trying alternative API for languages: {url}")

                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    # 更新主API端点为成功的备选端点
                    self.primary_api_url = alt_api_url
                    logger.info(f"Updated primary API endpoint to: {self.primary_api_url}")

                    return response.json()
            except Exception as e:
                errors.append(f"Alternative API {alt_api_url} error: {str(e)}")
                logger.warning(f"Alternative API failed for languages: {str(e)}")

        # 如果所有API端点都失败，返回一个基本的语言列表
        logger.error(f"All Lingva API endpoints failed for languages: {errors}")

        # 返回一个基本的语言列表，以便服务仍然可以运行
        return [
            {"code": "auto", "name": "Detect Language"},
            {"code": "en", "name": "English"},
            {"code": "zh", "name": "Chinese"},
            # 其他基本语言...
        ]

    async def translate_text(self, text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """向Lingva Translate API发送翻译请求"""
        errors = []
        encoded_text = urllib.parse.quote(text)

        # 首先尝试主API端点
        try:
            url = f"{self.primary_api_url}/{source_lang}/{target_lang}/{encoded_text}"
            logger.info(f"Sending translation request to: {url}")

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                logger.info(f"Response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()

                return {
                    "original_text": text,
                    "translated_text": data["translation"],
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            errors.append(f"Primary API error: {str(e)}")
            logger.warning(f"Primary API failed, trying alternatives: {str(e)}")

        # 尝试备选端点
        for alt_api_url in self.api_alternatives:
            if alt_api_url == self.primary_api_url:
                continue

            try:
                url = f"{alt_api_url}/{source_lang}/{target_lang}/{encoded_text}"
                logger.info(f"Trying alternative API: {url}")

                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()

                    # 更新主API端点
                    self.primary_api_url = alt_api_url
                    logger.info(f"Updated primary API endpoint to: {self.primary_api_url}")

                    return {
                        "original_text": text,
                        "translated_text": data["translation"],
                        "source_language": source_lang,
                        "target_language": target_lang,
                        "timestamp": datetime.now().isoformat(),
                        "api_used": alt_api_url
                    }
            except Exception as e:
                errors.append(f"Alternative API {alt_api_url} error: {str(e)}")
                logger.warning(f"Alternative API failed: {str(e)}")

        # 所有API端点都失败
        error_message = "\n".join(errors)
        logger.error(f"All Lingva API endpoints failed: {error_message}")
        raise RuntimeError(f"All Lingva API endpoints failed: {error_message}")