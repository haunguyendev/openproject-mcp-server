"""Work package management tools - Priority CRITICAL tools for 12 users."""

import json
from typing import Optional
from pydantic import BaseModel, Field

from src.server import mcp, get_client
from src.utils.formatting import (
    format_work_package_list,
    format_work_package_detail,
    format_success,
    format_error,
)


# Pydantic models for type-safe input validation
class CreateWorkPackageInput(BaseModel):
    """Input model for creating work packages with validation."""

    project_id: int = Field(..., description="Project ID where work package will be created", gt=0)
    subject: str = Field(..., description="Work package title/subject", min_length=1, max_length=255)
    type_id: int = Field(..., description="Type ID (use list_types to see available types)", gt=0)
    description: Optional[str] = Field(None, description="Detailed description in raw format")
    start_date: Optional[str] = Field(None, description="Start date in ISO format (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Due date in ISO format (YYYY-MM-DD)")
    assignee_id: Optional[int] = Field(None, description="Assignee user ID", gt=0)
    status_id: Optional[int] = Field(None, description="Status ID", gt=0)
    priority_id: Optional[int] = Field(None, description="Priority ID", gt=0)


class UpdateWorkPackageInput(BaseModel):
    """Input model for updating work packages with validation."""

    work_package_id: int = Field(..., description="Work package ID to update", gt=0)
    subject: Optional[str] = Field(None, description="New subject/title", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="New description")
    type_id: Optional[int] = Field(None, description="New type ID", gt=0)
    status_id: Optional[int] = Field(None, description="New status ID", gt=0)
    priority_id: Optional[int] = Field(None, description="New priority ID", gt=0)
    assignee_id: Optional[int] = Field(None, description="New assignee user ID", gt=0)
    start_date: Optional[str] = Field(None, description="New start date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="New due date (YYYY-MM-DD)")
    percentage_done: Optional[int] = Field(None, description="Progress percentage (0-100)", ge=0, le=100)


@mcp.tool
async def list_work_packages(
    project_id: Optional[int] = None,
    active_only: bool = True,
    offset: int = 0,
    page_size: int = 20
) -> str:
    """List work packages (tasks) - CRITICAL tool for viewing all tasks.

    This is one of the most important tools for your 12 users to view and manage their work.

    Args:
        project_id: Optional project ID to filter work packages by project
        active_only: If True, only show work packages with open status (default: True)
        offset: Starting index for pagination (default: 0)
        page_size: Number of results per page (default: 20, max: 100)

    Returns:
        Formatted list of work packages with type, status, priority, assignee, and dates
    """
    try:
        client = get_client()

        # Build filters
        filters = None
        if active_only:
            # Filter for open statuses (not closed)
            filters = json.dumps([{"status": {"operator": "o", "values": []}}])

        # Validate pagination parameters
        if offset < 0:
            return format_error("offset must be >= 0")
        if page_size < 1 or page_size > 100:
            return format_error("page_size must be between 1 and 100")

        result = await client.get_work_packages(
            project_id=project_id,
            filters=filters,
            offset=offset,
            page_size=page_size
        )

        work_packages = result.get("_embedded", {}).get("elements", [])
        total = result.get("total", len(work_packages))

        # Format response
        text = format_work_package_list(work_packages)

        # Add pagination info
        if total > page_size:
            text += f"\n📄 **Pagination**: Showing {offset + 1}-{offset + len(work_packages)} of {total} total\n"
            text += f"   Use `offset={offset + page_size}` to see next page\n"

        return text

    except Exception as e:
        return format_error(f"Failed to list work packages: {str(e)}")


@mcp.tool
async def create_work_package(input: CreateWorkPackageInput) -> str:
    """Create a new work package (task) - CRITICAL tool for creating tasks.

    This is one of the most important tools for your 12 users to create new work items.

    Args:
        input: Work package data including project_id, subject, type_id, and optional fields

    Returns:
        Success message with created work package ID and details

    Example:
        To create a bug in project 5:
        {
            "project_id": 5,
            "subject": "Fix login issue",
            "type_id": 1,
            "description": "Users cannot login with valid credentials",
            "priority_id": 3,
            "assignee_id": 7,
            "due_date": "2025-01-15"
        }
    """
    try:
        client = get_client()

        # Build data dict for API
        data = {
            "project": input.project_id,
            "subject": input.subject,
            "type": input.type_id,
        }

        # Add optional fields
        if input.description:
            data["description"] = input.description
        if input.priority_id:
            data["priority_id"] = input.priority_id
        if input.assignee_id:
            data["assignee_id"] = input.assignee_id

        # Add date fields (use camelCase for API)
        if input.start_date:
            data["startDate"] = input.start_date
        if input.due_date:
            data["dueDate"] = input.due_date

        # Create work package
        result = await client.create_work_package(data)

        # Format success response
        wp_id = result.get("id")
        wp_subject = result.get("subject")

        text = format_success(f"Work package #{wp_id} created successfully!\n\n")
        text += f"**Subject**: {wp_subject}\n"

        # Add embedded data
        embedded = result.get("_embedded", {})
        if "type" in embedded:
            text += f"**Type**: {embedded['type'].get('name', 'Unknown')}\n"
        if "status" in embedded:
            text += f"**Status**: {embedded['status'].get('name', 'Unknown')}\n"
        if "priority" in embedded:
            text += f"**Priority**: {embedded['priority'].get('name', 'Unknown')}\n"
        if "assignee" in embedded:
            text += f"**Assignee**: {embedded['assignee'].get('name', 'Unassigned')}\n"

        if result.get('startDate'):
            text += f"**Start Date**: {result['startDate']}\n"
        if result.get('dueDate'):
            text += f"**Due Date**: {result['dueDate']}\n"

        return text

    except Exception as e:
        return format_error(f"Failed to create work package: {str(e)}")


@mcp.tool
async def update_work_package(input: UpdateWorkPackageInput) -> str:
    """Update an existing work package (task) - CRITICAL tool for updating tasks.

    This is one of the most important tools for your 12 users to update work items,
    including changing status, assignee, dates, and progress.

    Args:
        input: Work package update data including work_package_id and fields to update

    Returns:
        Success message with updated work package details

    Example:
        To update work package #123 status and assignee:
        {
            "work_package_id": 123,
            "status_id": 5,
            "assignee_id": 7,
            "percentage_done": 50,
            "due_date": "2025-01-20"
        }
    """
    try:
        client = get_client()

        # Build data dict for API (only include provided fields)
        data = {}

        if input.subject is not None:
            data["subject"] = input.subject
        if input.description is not None:
            data["description"] = input.description
        if input.type_id is not None:
            data["type_id"] = input.type_id
        if input.status_id is not None:
            data["status_id"] = input.status_id
        if input.priority_id is not None:
            data["priority_id"] = input.priority_id
        if input.assignee_id is not None:
            data["assignee_id"] = input.assignee_id
        if input.percentage_done is not None:
            data["percentage_done"] = input.percentage_done

        # Add date fields (use camelCase for API)
        if input.start_date is not None:
            data["startDate"] = input.start_date
        if input.due_date is not None:
            data["dueDate"] = input.due_date

        if not data:
            return format_error("No fields provided to update")

        # Update work package
        result = await client.update_work_package(input.work_package_id, data)

        # Format success response
        wp_id = result.get("id")
        wp_subject = result.get("subject")

        text = format_success(f"Work package #{wp_id} updated successfully!\n\n")
        text += f"**Subject**: {wp_subject}\n"

        # Add embedded data
        embedded = result.get("_embedded", {})
        if "type" in embedded:
            text += f"**Type**: {embedded['type'].get('name', 'Unknown')}\n"
        if "status" in embedded:
            text += f"**Status**: {embedded['status'].get('name', 'Unknown')}\n"
        if "priority" in embedded:
            text += f"**Priority**: {embedded['priority'].get('name', 'Unknown')}\n"
        if "assignee" in embedded:
            text += f"**Assignee**: {embedded['assignee'].get('name', 'Unassigned')}\n"

        if result.get('startDate'):
            text += f"**Start Date**: {result['startDate']}\n"
        if result.get('dueDate'):
            text += f"**Due Date**: {result['dueDate']}\n"
        if 'percentageDone' in result:
            text += f"**Progress**: {result['percentageDone']}%\n"

        return text

    except Exception as e:
        return format_error(f"Failed to update work package: {str(e)}")
