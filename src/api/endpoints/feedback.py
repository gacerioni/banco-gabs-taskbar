"""
Feedback Endpoints
For continuous learning of the Intent Router
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
import json
import time

from ...data import get_redis_client
from ...routers.intent_router import force_reload_routers

router = APIRouter()

# Redis key for the feedback queue
FEEDBACK_QUEUE_KEY = "app:router:feedback_queue"

class FeedbackSubmit(BaseModel):
    query: str
    detected_intent: str
    expected_intent: str
    language: str = "pt"

@router.post("/api/feedback")
async def submit_feedback(feedback: FeedbackSubmit) -> Dict[str, Any]:
    """
    Submit user feedback when the router makes a mistake.
    Pushes to a Redis List for admin review.
    """
    try:
        redis_client = get_redis_client()
        
        feedback_item = {
            "id": f"fb_{int(time.time()*1000)}",
            "query": feedback.query,
            "detected_intent": feedback.detected_intent,
            "expected_intent": feedback.expected_intent,
            "language": feedback.language,
            "timestamp": time.time()
        }
        
        # Add to the end of the list
        redis_client.rpush(FEEDBACK_QUEUE_KEY, json.dumps(feedback_item, ensure_ascii=False))
        
        return {"status": "success", "message": "Feedback submitted for review"}
        
    except Exception as e:
        print(f"⚠️ Error saving feedback: {e}")
        # Return success anyway so we don't break the UI
        return {"status": "success", "message": "Feedback noted"}


@router.get("/admin/api/feedback")
async def get_pending_feedback() -> Dict[str, Any]:
    """Get all pending feedback from the queue"""
    try:
        redis_client = get_redis_client()
        
        # Get all items from the list
        items = redis_client.lrange(FEEDBACK_QUEUE_KEY, 0, -1)
        
        feedback_list = []
        for item in items:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            feedback_list.append(json.loads(item))
            
        return {
            "status": "success",
            "total": len(feedback_list),
            "feedback": feedback_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FeedbackAction(BaseModel):
    id: str
    query: str
    expected_intent: str
    language: str

@router.post("/admin/api/feedback/approve")
async def approve_feedback(action: FeedbackAction) -> Dict[str, Any]:
    """
    Approve feedback:
    1. Add it to the JSONL router examples
    2. Force reload the Semantic Router
    3. Remove from queue
    """
    try:
        redis_client = get_redis_client()
        
        # 1. Add to JSONL
        file_path = f"src/data/seed/router_examples/{action.language}_{action.expected_intent}.jsonl"
        
        new_example = {
            "example": action.query,
            "intent": action.expected_intent,
            "language": action.language,
            "category": "user_feedback"
        }
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(new_example, ensure_ascii=False) + '\n')
            
        # 2. Remove from queue (we read all, filter out the approved one, delete queue, push rest back)
        # This is a simple implementation for demo purposes
        items = redis_client.lrange(FEEDBACK_QUEUE_KEY, 0, -1)
        redis_client.delete(FEEDBACK_QUEUE_KEY)
        
        for item in items:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            item_obj = json.loads(item)
            if item_obj["id"] != action.id:
                redis_client.rpush(FEEDBACK_QUEUE_KEY, json.dumps(item_obj, ensure_ascii=False))
                
        # 3. Reload routers!
        print(f"🔄 Feedback approved for '{action.query}'. Reloading routers...")
        force_reload_routers()
        
        return {"status": "success", "message": f"Added '{action.query}' to {action.expected_intent} and reloaded router!"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/api/feedback/discard")
async def discard_feedback(action: FeedbackAction) -> Dict[str, Any]:
    """Discard feedback: just remove from queue"""
    try:
        redis_client = get_redis_client()
        
        items = redis_client.lrange(FEEDBACK_QUEUE_KEY, 0, -1)
        redis_client.delete(FEEDBACK_QUEUE_KEY)
        
        for item in items:
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            item_obj = json.loads(item)
            if item_obj["id"] != action.id:
                redis_client.rpush(FEEDBACK_QUEUE_KEY, json.dumps(item_obj, ensure_ascii=False))
                
        return {"status": "success", "message": "Feedback discarded"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
