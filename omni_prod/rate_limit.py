from __future__ import annotations
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int

class InMemoryFixedWindowLimiter:
    """Development/single-instance limiter. Production should use RedisFixedWindowLimiter."""
    def __init__(self, *, limit:int=60, window_seconds:int=60, clock=time.time):
        if limit<1 or window_seconds<1: raise ValueError('invalid rate limit')
        self.limit=limit; self.window_seconds=window_seconds; self.clock=clock; self._state={}
    def check(self,key:str)->RateLimitDecision:
        now=int(self.clock()); window=now//self.window_seconds; k=(key,window)
        count=self._state.get(k,0)+1; self._state[k]=count
        allowed=count<=self.limit; remaining=max(0,self.limit-count); retry=(window+1)*self.window_seconds-now
        return RateLimitDecision(allowed,remaining,retry if not allowed else 0)

class RedisFixedWindowLimiter:
    def __init__(self, redis, *, limit:int=60, window_seconds:int=60, prefix='omni:rl'):
        if limit<1 or window_seconds<1: raise ValueError('invalid rate limit')
        self.redis=redis; self.limit=limit; self.window_seconds=window_seconds; self.prefix=prefix
    def check(self,key:str)->RateLimitDecision:
        now=int(time.time()); window=now//self.window_seconds; rk=f'{self.prefix}:{window}:{key}'
        pipe=self.redis.pipeline(); pipe.incr(rk); pipe.expire(rk,self.window_seconds+2); count,_=pipe.execute(); count=int(count)
        return RateLimitDecision(count<=self.limit,max(0,self.limit-count),((window+1)*self.window_seconds-now) if count>self.limit else 0)
