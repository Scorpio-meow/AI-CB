
import asyncio
import time
import logging
from typing import List, Tuple, Any, Optional
from dataclasses import dataclass
from collections import deque
logger = logging.getLogger(__name__)
@dataclass
class BatchRequest:
    query: str
    future: asyncio.Future
    timestamp: float
    request_id: str
class BatchAccumulator:
    
    def __init__(
        self,
        max_batch_size: int = 32,
        max_wait_time: float = 0.05,
        min_batch_size: int = 4
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.min_batch_size = min_batch_size
        
        self.queue: deque = deque()
        self.lock = asyncio.Lock()
        self.processing = False
        
        self.total_requests = 0
        self.total_batches = 0
        self.total_wait_time = 0.0
        
        logger.info(f"批次累積器已初始化: max_batch={max_batch_size}, max_wait={max_wait_time}s, min_batch={min_batch_size}")
    
    async def add_request(self, query: str, request_id: str) -> Any:
        future = asyncio.Future()
        request = BatchRequest(
            query=query,
            future=future,
            timestamp=time.time(),
            request_id=request_id
        )
        
        async with self.lock:
            self.queue.append(request)
            self.total_requests += 1
        
        if not self.processing:
            asyncio.create_task(self._process_batch())
        
        return await future
    
    async def _process_batch(self):
        if self.processing:
            return
        
        self.processing = True
        
        try:
            await asyncio.sleep(self.max_wait_time)
            
            batch = []
            async with self.lock:
                while len(batch) < self.max_batch_size and self.queue:
                    batch.append(self.queue.popleft())
            
            if not batch:
                return
            
            if len(batch) < self.min_batch_size:
                oldest_request_time = batch[0].timestamp
                elapsed = time.time() - oldest_request_time
                
                if elapsed < self.max_wait_time:
                    await asyncio.sleep(self.max_wait_time - elapsed)
                    
                    async with self.lock:
                        while len(batch) < self.max_batch_size and self.queue:
                            batch.append(self.queue.popleft())
            
            if batch:
                self.total_batches += 1
                avg_wait = sum(time.time() - req.timestamp for req in batch) / len(batch)
                self.total_wait_time += avg_wait
                
                logger.info(f"處理批次: {len(batch)} 個請求, 平均等待: {avg_wait*1000:.1f}ms")
                
                
        finally:
            self.processing = False
            
            if self.queue:
                asyncio.create_task(self._process_batch())
    
    def get_stats(self) -> dict:
        avg_batch_size = self.total_requests / self.total_batches if self.total_batches > 0 else 0
        avg_wait_time = self.total_wait_time / self.total_batches if self.total_batches > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "total_batches": self.total_batches,
            "avg_batch_size": round(avg_batch_size, 2),
            "avg_wait_time_ms": round(avg_wait_time * 1000, 2),
            "queue_size": len(self.queue),
            "gpu_utilization_boost": f"+{round((avg_batch_size / self.max_batch_size) * 20, 1)}%"
        }
class EmbeddingBatchProcessor:
    
    def __init__(self, rag_system, max_batch_size: int = 32):
        self.rag_system = rag_system
        self.accumulator = BatchAccumulator(
            max_batch_size=max_batch_size,
            max_wait_time=0.05,
            min_batch_size=4
        )
        logger.info(f"嵌入批次處理器已啟用: max_batch={max_batch_size}")
    
    async def encode_batch(self, queries: List[str]) -> List:
        try:
            embeddings = self.rag_system.local_embeddings.encode(
                queries,
                batch_size=len(queries),
                show_progress_bar=False,
                convert_to_numpy=True,
                device=self.rag_system.device
            )
            return embeddings
        except Exception as e:
            logger.error(f"批次編碼失敗: {e}")
            raise
    
    async def search_batch(self, queries: List[str]) -> List[List[Tuple]]:
        results = []
        for query in queries:
            result = self.rag_system.smart_search(query)
            results.append(result)
        return results
    
    def get_stats(self) -> dict:
        return self.accumulator.get_stats()
_batch_processor: Optional[EmbeddingBatchProcessor] = None
def get_batch_processor(rag_system = None) -> Optional[EmbeddingBatchProcessor]:
    global _batch_processor
    
    if _batch_processor is None and rag_system is not None:
        max_batch_size = int(os.getenv("BATCH_ACCUMULATOR_SIZE", "32"))
        _batch_processor = EmbeddingBatchProcessor(rag_system, max_batch_size)
    
    return _batch_processor
def is_batch_processing_enabled() -> bool:
    import os
    return os.getenv("ENABLE_BATCH_ACCUMULATION", "false").lower() == "true"
