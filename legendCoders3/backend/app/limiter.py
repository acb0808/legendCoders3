from slowapi import Limiter
from slowapi.util import get_remote_address

# 전역 Limiter 인스턴스 초기화
limiter = Limiter(key_func=get_remote_address)
