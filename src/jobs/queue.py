"""
Job queue management for OCR processing.

This module provides functions for creating, tracking, and managing OCR processing jobs.
It uses Redis as a backend for job queue management and status tracking.
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union

import redis
from fastapi import HTTPException

# Redis configuration - would be externalized in production
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Redis key prefixes
JOB_PREFIX = "ocr:job:"
JOB_RESULT_PREFIX = "ocr:result:"
JOB_LIST = "ocr:jobs"

# Job retention period (in seconds)
JOB_RETENTION = 60 * 60 * 24  # 24 hours


# Redis client singleton
_redis_client = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
    return _redis_client


def create_job(file_name: str, file_type: str) -> Dict[str, Any]:
    """
    Create a new OCR processing job.
    
    Args:
        file_name: Original name of the uploaded file
        file_type: Type of file (pdf, image, pptx)
        
    Returns:
        Dictionary with job details including job_id
    """
    job_id = str(uuid.uuid4())
    
    # Create timestamp
    now = datetime.now().isoformat()
    
    # Create job data
    job_data = {
        "job_id": job_id,
        "file_name": file_name,
        "file_type": file_type,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    
    # Store job in Redis
    redis_client = get_redis_client()
    redis_client.setex(
        f"{JOB_PREFIX}{job_id}",
        JOB_RETENTION,
        json.dumps(job_data)
    )
    
    # Add job to list of jobs
    redis_client.zadd(JOB_LIST, {job_id: time.time()})
    
    return job_data


def get_job(job_id: str) -> Dict[str, Any]:
    """
    Get job details by job ID.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Dictionary with job details
        
    Raises:
        HTTPException: If job not found
    """
    redis_client = get_redis_client()
    job_data = redis_client.get(f"{JOB_PREFIX}{job_id}")
    
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return json.loads(job_data)


def update_job_status(job_id: str, status: str, progress: Optional[int] = None, 
                      message: Optional[str] = None) -> Dict[str, Any]:
    """
    Update job status.
    
    Args:
        job_id: Unique job identifier
        status: New job status (pending, processing, completed, failed)
        progress: Optional progress percentage (0-100)
        message: Optional status message
        
    Returns:
        Updated job data
        
    Raises:
        HTTPException: If job not found
    """
    redis_client = get_redis_client()
    job_key = f"{JOB_PREFIX}{job_id}"
    job_data_str = redis_client.get(job_key)
    
    if not job_data_str:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    job_data = json.loads(job_data_str)
    job_data["status"] = status
    job_data["updated_at"] = datetime.now().isoformat()
    
    # Update optional fields if provided
    if progress is not None:
        job_data["progress"] = progress
    
    if message is not None:
        job_data["message"] = message
    
    # Save updated job data
    redis_client.setex(
        job_key,
        JOB_RETENTION,
        json.dumps(job_data)
    )
    
    return job_data


def store_job_result(job_id: str, result: Dict[str, Any]) -> None:
    """
    Store job processing result.
    
    Args:
        job_id: Unique job identifier
        result: Result data to store
        
    Raises:
        HTTPException: If job not found
    """
    redis_client = get_redis_client()
    
    # Verify job exists
    if not redis_client.exists(f"{JOB_PREFIX}{job_id}"):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Store result
    redis_client.setex(
        f"{JOB_RESULT_PREFIX}{job_id}",
        JOB_RETENTION,
        json.dumps(result)
    )


def get_job_result(job_id: str) -> Dict[str, Any]:
    """
    Get job result by job ID.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Dictionary with job result data
        
    Raises:
        HTTPException: If job or result not found
    """
    redis_client = get_redis_client()
    
    # First check if job exists
    if not redis_client.exists(f"{JOB_PREFIX}{job_id}"):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Then check for result
    result_data = redis_client.get(f"{JOB_RESULT_PREFIX}{job_id}")
    
    if not result_data:
        job_data = get_job(job_id)
        if job_data.get("status") == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} failed: {job_data.get('message', 'Unknown error')}"
            )
        raise HTTPException(
            status_code=404, 
            detail=f"Result not available yet for job {job_id}"
        )
    
    return json.loads(result_data)


def clean_old_jobs() -> int:
    """
    Clean up old jobs from Redis.
    
    Returns:
        Number of jobs cleaned up
    """
    redis_client = get_redis_client()
    
    # Get jobs older than retention period
    cutoff = time.time() - JOB_RETENTION
    old_job_ids = redis_client.zrangebyscore(JOB_LIST, 0, cutoff)
    
    count = 0
    for job_id in old_job_ids:
        # Delete job data and result
        redis_client.delete(f"{JOB_PREFIX}{job_id}", f"{JOB_RESULT_PREFIX}{job_id}")
        count += 1
    
    # Remove from jobs list
    redis_client.zremrangebyscore(JOB_LIST, 0, cutoff)
    
    return count