"""
Rate limiters dependencies for API endpoints.

Rate limiting strategy:
1. Short-term rate limiting (1 second): Prevent sudden traffic, protect system stability
2. Medium-term rate limiting (30 seconds): Smooth traffic, avoid too many requests in a short period
3. Long-term rate limiting (1 hour): Total control, prevent long-term abuse

Different endpoint types:
- Read endpoints: More lenient, because read operations place less load on the system
- Write endpoints: More strict, because write operations require more resources

Configuration file location: env/rate_limiters.yaml
"""
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter

from portal.config import settings
from portal.schemas.rate_limiter import RateLimiterConfig


def create_rate_limiters(config: RateLimiterConfig) -> list:
    """
    從 RateLimiterConfig Model 建立限流器列表

    :param config: 限流器配置 Model
    :return: 限流器列表
    """
    return [
        Depends(RateLimiter(times=config.short.times, seconds=config.short.seconds)),
        Depends(RateLimiter(times=config.medium.times, seconds=config.medium.seconds)),
        Depends(RateLimiter(times=config.long.times, seconds=config.long.seconds)),
    ]


def get_rate_limiters_config(config_type: str = "default") -> RateLimiterConfig:
    """
    Get rate limiters configuration from the configuration file
    :param config_type: Configuration type (default, read, write, admin)
    :return:
    """
    if not settings.RATE_LIMITERS_CONFIG:
        # Return default values if no configuration is loaded
        from portal.schemas.rate_limiter import RateLimitWindow
        return RateLimiterConfig(
            short=RateLimitWindow(times=3, seconds=1),
            medium=RateLimitWindow(times=20, seconds=30),
            long=RateLimitWindow(times=400, seconds=3600),
        )

    # 根據配置類型取得對應的配置
    config_map = {
        "default": settings.RATE_LIMITERS_CONFIG.default,
        "read": settings.RATE_LIMITERS_CONFIG.read,
        "write": settings.RATE_LIMITERS_CONFIG.write,
    }

    return config_map.get(config_type, settings.RATE_LIMITERS_CONFIG.default)


# 預設限流器(用於一般端點)
DEFAULT_RATE_LIMITERS = create_rate_limiters(get_rate_limiters_config("default"))
# 讀取端點限流器(較寬鬆)
READ_RATE_LIMITERS = create_rate_limiters(get_rate_limiters_config("read"))
# 寫入端點限流器(較嚴格)
WRITE_RATE_LIMITERS = create_rate_limiters(get_rate_limiters_config("write"))
