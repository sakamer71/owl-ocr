"""
Router for job management endpoints.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.models.responses import JobResponse, ProcessingResult
from src.jobs.queue import get_job, get_job_result, clean_old_jobs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Get the status of a job by its ID",
)
async def get_job_status(job_id: str) -> JobResponse:
    """
    Get the status of a job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Job status information
    """
    try:
        job_data = get_job(job_id)
        return JobResponse(**job_data)
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")


@router.get(
    "/jobs/{job_id}/result",
    response_model=ProcessingResult,
    summary="Get job result",
    description="Get the result of a completed job by its ID",
)
async def get_job_results(job_id: str) -> ProcessingResult:
    """
    Get the result of a job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Job processing result
    """
    try:
        # First check job status
        job_data = get_job(job_id)
        
        # Check if job is completed
        if job_data["status"] != "completed":
            if job_data["status"] == "failed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Job {job_id} failed: {job_data.get('message', 'Unknown error')}"
                )
            else:
                raise HTTPException(
                    status_code=102, 
                    detail=f"Job {job_id} is still {job_data['status']}. Current progress: {job_data.get('progress', 0)}%"
                )
        
        # Get results
        result = get_job_result(job_id)
        return ProcessingResult(**result)
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting job result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting job result: {str(e)}")


@router.delete(
    "/jobs/{job_id}",
    response_model=dict,
    summary="Delete a job",
    description="Delete a job and its result data",
)
async def delete_job(job_id: str) -> dict:
    """
    Delete a job and its result data.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Status message
    """
    try:
        # This is a placeholder. In a real implementation, you would:
        # 1. Check if the job exists
        # 2. Delete any output files
        # 3. Remove the job from Redis
        # 4. Return success message
        
        # For now, we'll just return a message
        return {"status": "success", "message": f"Job {job_id} deleted"}
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")


@router.post(
    "/jobs/cleanup",
    response_model=dict,
    summary="Clean up old jobs",
    description="Remove old jobs and their results from storage",
)
async def cleanup_jobs() -> dict:
    """
    Clean up old jobs and their results.
    
    Returns:
        Status message with count of cleaned jobs
    """
    try:
        count = clean_old_jobs()
        return {"status": "success", "message": f"Cleaned up {count} old jobs"}
    except Exception as e:
        logger.error(f"Error cleaning up jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up jobs: {str(e)}")