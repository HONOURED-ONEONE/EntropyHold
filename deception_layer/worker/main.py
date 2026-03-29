import asyncio
import logging
from fastapi import FastAPI, HTTPException, Body
from contracts.models import DeliveryTask
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

app = FastAPI(title="Deception Layer Worker API", version="1.0.0")

class DeliveryWorker:
    """
    Durable worker service handling reporting/callback delivery using the final reports produced by the Python Behavioral Brain.
    """
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def process_task(self, task: DeliveryTask):
        """
        Consume final-report-ready work items or retrieval references.
        Manages retries/backoff/idempotency.
        """
        logger.info(f"Processing delivery task {task.taskId} for session {task.sessionId}")
        
        while task.retryCount <= self.max_retries:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(task.destinationUrl, json=task.reportPayload, timeout=10.0)
                    response.raise_for_status()
                
                logger.info(f"Task {task.taskId} delivered successfully.")
                return True
            except Exception as e:
                task.retryCount += 1
                logger.warning(f"Delivery failed for {task.taskId}: {e}. Retrying... ({task.retryCount}/{self.max_retries})")
                if task.retryCount <= self.max_retries:
                    await asyncio.sleep(2 ** task.retryCount) # Exponential backoff
        
        logger.error(f"Task {task.taskId} reached dead-letter queue after {self.max_retries} retries.")
        return False

worker = DeliveryWorker()

@app.get("/api/worker/health")
async def health_check():
    return {"status": "ok", "service": "worker"}

@app.post("/api/worker/delivery/trigger")
async def trigger_delivery(task: DeliveryTask):
    """Manual trigger or queue-pull entry point."""
    success = await worker.process_task(task)
    if not success:
        raise HTTPException(status_code=500, detail="Delivery failed after retries")
    return {"status": "delivered", "taskId": task.taskId}

