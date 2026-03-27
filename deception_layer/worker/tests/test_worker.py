import pytest
import asyncio
from worker.main import DeliveryWorker
from contracts.models import DeliveryTask

@pytest.mark.asyncio
async def test_worker_success():
    worker = DeliveryWorker()
    task = DeliveryTask(
        task_id="test-1",
        session_id="s1",
        report_payload={},
        destination_url="http://test.local"
    )
    result = await worker.process_task(task)
    assert result == True

@pytest.mark.asyncio
async def test_worker_retry():
    worker = DeliveryWorker(max_retries=1)
    task = DeliveryTask(
        task_id="test-2",
        session_id="s2",
        report_payload={},
        destination_url="bad-url"
    )
    # We can mock the network call to fail and test the retry logic here
    # For now, just ensure it initializes
    assert task.retry_count == 0
