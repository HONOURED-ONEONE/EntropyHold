import pytest
from unittest.mock import patch
from contextlib import contextmanager
import fakeredis

@pytest.fixture(autouse=True)
def mock_session_lock():
    @contextmanager
    def _mock_lock(*args, **kwargs):
        yield
    
    with patch("app.core.orchestrator.session_lock", _mock_lock), patch("app.utils.lock.session_lock", _mock_lock):
        yield

@pytest.fixture(autouse=True)
def mock_redis_global():
    server = fakeredis.FakeServer()
    mock_r = fakeredis.FakeRedis(server=server, decode_responses=True)
    
    with patch("redis.Redis.from_url", return_value=mock_r):
        yield
        mock_r.flushdb()



