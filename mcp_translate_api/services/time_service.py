import logging
import pytz
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("time-service")

class TimeService:
    """时间服务类"""
    
    @staticmethod
    async def get_current_time(timezone: str = "UTC", format_str: str = "%Y-%m-%d %H:%M:%S") -> Dict[str, Any]:
        """获取指定时区的当前时间"""
        try:
            # 获取当前UTC时间
            utc_now = datetime.now(pytz.UTC)

            # 转换到指定时区
            if timezone not in pytz.all_timezones:
                # 如果时区无效，记录警告并使用UTC
                logger.warning(f"Invalid timezone: {timezone}, using UTC instead")
                timezone = "UTC"

            local_now = utc_now.astimezone(pytz.timezone(timezone))

            # 格式化时间
            formatted_time = local_now.strftime(format_str)

            # 返回结果
            return {
                "current_time": formatted_time,
                "timezone": timezone,
                "format": format_str,
                "utc_time": utc_now.strftime(format_str),
                "timestamp": utc_now.timestamp()
            }
        except Exception as e:
            logger.error(f"Error getting current time: {str(e)}")
            raise RuntimeError(f"Error getting current time: {str(e)}")