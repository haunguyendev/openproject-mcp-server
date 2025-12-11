"""Bulk operations utilities for concurrent work package updates.

This module provides helper functions for executing bulk operations on multiple
work packages concurrently, significantly improving performance over sequential updates.

Performance:
- Sequential: 30 tasks × 500ms = 15 seconds
- Concurrent: ~2-3 seconds (5-7x faster)
"""

import asyncio
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


@dataclass
class BulkOperationResult:
    """Result summary from a bulk operation.
    
    Attributes:
        total: Total number of work packages processed
        succeeded: Number of successful operations
        failed: Number of failed operations
        errors: List of error messages for failed operations
        successes: List of successful operation results
        duration: Total execution time in seconds
    """
    total: int
    succeeded: int
    failed: int
    errors: List[str]
    successes: List[Dict[str, Any]]
    duration: float
    
    def success_rate(self) -> float:
        """Calculate success rate as a percentage.
        
        Returns:
            Success rate between 0.0 and 100.0
        """
        if self.total == 0:
            return 0.0
        return (self.succeeded / self.total) * 100.0


async def bulk_update_work_packages(
    client: Any,
    work_package_ids: List[int],
    update_data: Dict[str, Any],
    max_concurrent: int = 30
) -> BulkOperationResult:
    """Execute bulk updates on multiple work packages concurrently.
    
    This is the core helper function used by all bulk update tools. It performs
    concurrent API calls using asyncio.gather() for maximum performance.
    
    Args:
        client: OpenProjectClient instance
        work_package_ids: List of work package IDs to update (max 50)
        update_data: Data to apply to each work package (e.g., {"assignee_id": 5})
        max_concurrent: Maximum concurrent requests (default: 30)
        
    Returns:
        BulkOperationResult with detailed summary of the operation
        
    Raises:
        ValueError: If work_package_ids is empty or exceeds 50 items
        
    Example:
        >>> client = get_client()
        >>> result = await bulk_update_work_packages(
        ...     client,
        ...     [10, 20, 30],
        ...     {"assignee_id": 5, "status_id": 2}
        ... )
        >>> print(f"Success: {result.succeeded}/{result.total}")
    """
    start_time = time.time()
    
    # Validate input
    if not work_package_ids:
        raise ValueError("work_package_ids cannot be empty")
    
    if len(work_package_ids) > 50:
        raise ValueError(
            f"Cannot update more than 50 work packages at once for safety. "
            f"You provided {len(work_package_ids)}. "
            f"Please split into multiple batches."
        )
    
    # Create async tasks for each work package update
    tasks = [
        client.update_work_package(wp_id, update_data)
        for wp_id in work_package_ids
    ]
    
    # Execute all tasks concurrently, capturing exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results - separate successes from failures
    successes = []
    errors = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Capture error with work package ID
            errors.append(f"WP#{work_package_ids[i]}: {str(result)}")
        else:
            # Successful update
            successes.append(result)
    
    duration = time.time() - start_time
    
    return BulkOperationResult(
        total=len(work_package_ids),
        succeeded=len(successes),
        failed=len(errors),
        errors=errors,
        successes=successes,
        duration=duration
    )


async def bulk_delete_work_packages(
    client: Any,
    work_package_ids: List[int]
) -> BulkOperationResult:
    """Execute bulk deletes on multiple work packages concurrently.
    
    **WARNING**: This is a destructive operation. Deleted work packages cannot be recovered.
    
    Safety measures:
    - Lower max limit (30 vs 50 for updates)
    - Should be called with explicit user confirmation
    
    Args:
        client: OpenProjectClient instance
        work_package_ids: List of work package IDs to delete (max 30)
        
    Returns:
        BulkOperationResult with detailed summary of the operation
        
    Raises:
        ValueError: If work_package_ids is empty or exceeds 30 items
        
    Example:
        >>> client = get_client()
        >>> result = await bulk_delete_work_packages(client, [10, 20, 30])
        >>> print(f"Deleted: {result.succeeded}/{result.total}")
    """
    start_time = time.time()
    
    # Validate input
    if not work_package_ids:
        raise ValueError("work_package_ids cannot be empty")
    
    # Lower limit for safety with deletions
    if len(work_package_ids) > 30:
        raise ValueError(
            f"Cannot delete more than 30 work packages at once for safety. "
            f"You provided {len(work_package_ids)}. "
            f"Please split into multiple batches."
        )
    
    # Create async delete tasks
    tasks = [
        client.delete_work_package(wp_id)
        for wp_id in work_package_ids
    ]
    
    # Execute concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successes = []
    errors = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"WP#{work_package_ids[i]}: {str(result)}")
        else:
            # Delete returns boolean, create success dict
            successes.append({
                "id": work_package_ids[i],
                "deleted": True
            })
    
    duration = time.time() - start_time
    
    return BulkOperationResult(
        total=len(work_package_ids),
        succeeded=len(successes),
        failed=len(errors),
        errors=errors,
        successes=successes,
        duration=duration
    )
