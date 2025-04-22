import logging
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv

# 导入服务类
from services.time_service import TimeService

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("time-api-server")

# 初始化服务
time_service = TimeService()

# 创建FastAPI应用
app = FastAPI(
    title="Time Service API",
    description="时间服务API",
    version="1.0.0"
)

# 定义请求模型
class TimeRequest(BaseModel):
    timezone: str = "UTC"
    format: str = "%Y-%m-%d %H:%M:%S"

# 定义API路由
@app.post("/api/time")
async def get_time(request: TimeRequest):
    """获取指定时区的当前时间"""
    try:
        result = await time_service.get_current_time(
            request.timezone,
            request.format
        )
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取时间失败: {str(e)}")

@app.get("/api/time")
async def get_time_get(
    timezone: str = "UTC",
    format: str = "%Y-%m-%d %H:%M:%S"
):
    """GET方式获取指定时区的当前时间"""
    try:
        result = await time_service.get_current_time(timezone, format)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取时间失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取时间失败: {str(e)}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="时间服务 API 服务器")
    parser.add_argument("--port", type=int, default=8002, help="服务器端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机")
    args = parser.parse_args()

    print(f"启动时间服务 API 服务器在端口 {args.port}...")
    uvicorn.run(app, host=args.host, port=args.port)