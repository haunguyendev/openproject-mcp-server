"""Bulk operations tools for work packages.

This module provides MCP tools for performing bulk operations on multiple
work packages simultaneously, significantly reducing manual effort.
"""

import json
import asyncio
import time
from typing import List, Optional
from datetime import date

from src.server import mcp, get_client
from src.utils.bulk_operations import (
    bulk_update_work_packages,
    bulk_delete_work_packages,
    BulkOperationResult
)
from src.utils.formatting import format_success, format_error


# ... [Previous 7 tools remain unchanged] ...


@mcp.tool
async def bulk_add_comment(
    work_package_ids: str,
    comment: str,
    internal: bool = False
) -> str:
    """Add the same comment to multiple work packages.
    
    Useful for status updates, notifications, or bulk communication.
    Max 50 work packages per call.
    
    Args:
        work_package_ids: Comma-separated work package IDs (e.g., "10,20,30") - max 50
        comment: Comment text to add (supports markdown)
        internal: If True, comment is only visible to project members (default: False)
        
    Returns:
        Success/failure summary
        
    Example:
        Add comment "Please review by Friday" to tasks #10, #20, #30:
        {
            "work_package_ids": "10,20,30",
            "comment": "Please review by Friday",
            "internal": false
        }
    """
    try:
        client = get_client()
        
        # Parse comma-separated IDs
        try:
            wp_ids = [int(id.strip()) for id in work_package_ids.split(",") if id.strip()]
        except ValueError:
            return format_error("work_package_ids must be comma-separated integers")
        
        # Validation
        if not wp_ids:
            return format_error("work_package_ids cannot be empty")
        if len(wp_ids) > 50:
            return format_error(f"Max 50 work packages (got {len(wp_ids)})")
        if not comment or not comment.strip():
            return format_error("Comment cannot be empty")
        
        # Create async tasks for adding comments
        tasks = [
            client.add_work_package_comment(wp_id, comment, internal)
            for wp_id in wp_ids
        ]
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Process results
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        errors = [str(r) for r in results if isinstance(r, Exception)]
        
        # Format response
        comment_preview = comment[:50] + "..." if len(comment) > 50 else comment
        
        text = f"✅ **Bulk Comment Complete!**\n\n"
        text += f"**Comment**: \"{comment_preview}\"\n"
        text += f"**Internal**: {internal}\n"
        text += f"**Total**: {len(wp_ids)} | **Success**: {successes} | **Failed**: {failures}\n"
        text += f"**Success Rate**: {(successes/len(wp_ids)*100) if wp_ids else 0:.1f}%\n"
        text += f"**Duration**: {duration:.2f}s\n\n"
        
        if failures > 0:
            text += f"**Errors** (first 5):\n"
            for i, error in enumerate(errors[:5], 1):
                text += f"{i}. {error}\n"
            if failures > 5:
                text += f"... and {failures - 5} more\n"
        
        if successes > 0:
            text += f"\n✅ Comment added to {successes} work package(s)\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk comment failed: {str(e)}")


@mcp.tool
async def bulk_update_filtered_work_packages(
    # Filter criteria (reuse from list_work_packages)
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    priority_ids: Optional[str] = None,
    type_ids: Optional[str] = None,
    status_ids: Optional[str] = None,
    overdue_only: bool = False,
    unassigned_only: bool = False,
    
    # Update data
    update_assignee_id: Optional[int] = None,
    update_status_id: Optional[int] = None,
    update_priority_id: Optional[int] = None,
    update_version_id: Optional[int] = None,
    
    # Safety
    dry_run: bool = True,
    max_results: int = 50
) -> str:
    """Apply bulk update to work packages matching filter criteria.
    
    This is the MOST POWERFUL bulk operation tool - combines flexible
    filtering with bulk updates.
    
    **SAFETY**: dry_run=True by default - shows preview without updating.
    Set dry_run=False to execute the updates.
    
    Args:
        # Filter params (same as list_work_packages)
        project_id: Filter by project
        assignee_id: Filter by assignee  
        priority_ids: Comma-separated priority IDs
        type_ids: Comma-separated type IDs
        status_ids: Comma-separated status IDs
        overdue_only: Only overdue tasks
        unassigned_only: Only unassigned tasks
        
        # Update params
        update_assignee_id: New assignee to set
        update_status_id: New status to set
        update_priority_id: New priority to set
        update_version_id: New version to set
        
        # Safety params
        dry_run: If True, only show preview (default: True)
        max_results: Max work packages to update (default: 50)
        
    Returns:
        Preview (if dry_run=True) or update summary (if dry_run=False)
        
    Example 1 - PREVIEW:
        Preview: Assign all overdue unassigned tasks to user #5:
        {
            "overdue_only": true,
            "unassigned_only": true,
            "update_assignee_id": 5,
            "dry_run": true
        }
        
    Example 2 - EXECUTE:
        Execute the update:
        {
            "overdue_only": true,
            "unassigned_only": true,
            "update_assignee_id": 5,
            "dry_run": false
        }
    """
    try:
        client = get_client()
        
        # Build filters (reuse logic from list_work_packages)
        filters_list = []
        
        # Status filter
        if status_ids:
            # Parse comma-separated IDs
            sids = [s.strip() for s in status_ids.split(",") if s.strip()]
            if sids:
                filters_list.append({"status": {"operator": "=", "values": sids}})
        elif overdue_only:
            filters_list.append({"status": {"operator": "o", "values": []}})
            filters_list.append({
                "dueDate": {
                    "operator": "<>d",
                    "values": ["2000-01-01", date.today().isoformat()]
                }
            })
        else:
            filters_list.append({"status": {"operator": "o", "values": []}})
        
        # Assignee filter
        if unassigned_only:
            filters_list.append({"assignee": {"operator": "!*", "values": []}})
        elif assignee_id:
            filters_list.append({"assignee": {"operator": "=", "values": [str(assignee_id)]}})
        
        # Priority filter
        if priority_ids:
            pids = [p.strip() for p in priority_ids.split(",") if p.strip()]
            if pids:
                filters_list.append({"priority": {"operator": "=", "values": pids}})
        
        # Type filter
        if type_ids:
            tids = [t.strip() for t in type_ids.split(",") if t.strip()]
            if tids:
                filters_list.append({"type": {"operator": "=", "values": tids}})
        
        filters = json.dumps(filters_list) if filters_list else None
        
        # Query work packages matching filter
        result = await client.get_work_packages(
            project_id=project_id,
            filters=filters,
            page_size=max_results
        )
        
        work_packages = result.get("_embedded", {}).get("elements", [])
        total_found = result.get("total", 0)
        
        if not work_packages:
            return "✅ No work packages match the filter criteria."
        
        # Build update data
        update_data = {}
        if update_assignee_id is not None:
            update_data["assignee_id"] = update_assignee_id
        if update_status_id is not None:
            update_data["status_id"] = update_status_id
        if update_priority_id is not None:
            update_data["priority_id"] = update_priority_id
        if update_version_id is not None:
            update_data["version_id"] = update_version_id
        
        if not update_data:
            return format_error("At least one update field must be provided")
        
        # DRY RUN MODE
        if dry_run:
            text = f"🔍 **DRY RUN - Preview of Bulk Update**\n\n"
            text += f"**Filter Matched**: {total_found} work package(s)\n"
            text += f"**Will Update**: {len(work_packages)} work package(s) (max: {max_results})\n\n"
            
            text += f"**Updates to Apply**:\n"
            for key, value in update_data.items():
                text += f"- {key}: {value}\n"
            
            text += f"\n**Preview of Affected Work Packages** (first 10):\n"
            for wp in work_packages[:10]:
                text += f"- #{wp.get('id')}: {wp.get('subject', 'Unknown')}\n"
            
            if len(work_packages) > 10:
                text += f"... and {len(work_packages) - 10} more\n"
            
            text += f"\n⚠️ **This is a DRY RUN** - No changes were made.\n"
            text += f"To execute, call again with: dry_run=false\n"
            
            return text
        
        # EXECUTE MODE
        wp_ids = [wp["id"] for wp in work_packages]
        
        # Execute bulk update
        bulk_result = await bulk_update_work_packages(client, wp_ids, update_data)
        
        # Format response
        text = f"✅ **Bulk Update Complete!**\n\n"
        text += f"**Filter Matched**: {total_found} total\n"
        text += f"**Updated**: {bulk_result.succeeded}/{bulk_result.total}\n"
        text += f"**Failed**: {bulk_result.failed}\n"
        text += f"**Success Rate**: {bulk_result.success_rate():.1f}%\n"
        text += f"**Duration**: {bulk_result.duration:.2f}s\n\n"
        
        if bulk_result.failed > 0:
            text += f"**Errors** (first 3):\n"
            for i, error in enumerate(bulk_result.errors[:3], 1):
                text += f"{i}. {error}\n"
        
        if bulk_result.succeeded > 0:
            text += f"\n**Updated Work Packages** (first 5):\n"
            for wp in bulk_result.successes[:5]:
                text += f"- #{wp.get('id')}: {wp.get('subject', 'Unknown')}\n"
            if bulk_result.succeeded > 5:
                text += f"... and {bulk_result.succeeded - 5} more\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk filtered update failed: {str(e)}")
