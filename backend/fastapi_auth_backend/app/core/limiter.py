from slowapi import Limiter
from slowapi.util import get_remote_address
# Replace with Redis storage for multiple workers/instances.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
