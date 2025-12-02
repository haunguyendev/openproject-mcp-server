"""Project management tools."""

import json
from typing import Optional
from src.server import mcp, get_client
from src.utils.formatting import format_project_list


@mcp.tool
async def list_projects(active_only: bool = True) -> str:
    """List all OpenProject projects.

    Args:
        active_only: If True, only show active projects (default: True)

    Returns:
        Formatted list of projects with their status and basic information
    """
    try:
        client = get_client()

        # Build filters
        filters = None
        if active_only:
            filters = json.dumps([{"active": {"operator": "=", "values": ["t"]}}])

        result = await client.get_projects(filters)
        projects = result.get("_embedded", {}).get("elements", [])

        return format_project_list(projects)

    except Exception as e:
        return f"❌ Failed to list projects: {str(e)}"


@mcp.tool
async def get_project(project_id: int) -> str:
    """Get detailed information about a specific project.

    Args:
        project_id: The project ID

    Returns:
        Detailed project information including description and settings
    """
    try:
        client = get_client()
        project = await client.get_project(project_id)

        text = f"✅ Project #{project.get('id')}\n\n"
        text += f"**Name**: {project.get('name', 'Unknown')}\n"
        text += f"**Identifier**: {project.get('identifier', 'N/A')}\n"
        text += f"**Status**: {'Active' if project.get('active') else 'Inactive'}\n"
        text += f"**Public**: {'Yes' if project.get('public') else 'No'}\n"

        if project.get('description'):
            desc = project['description']
            if isinstance(desc, dict):
                desc_text = desc.get('raw', '')
            else:
                desc_text = str(desc)
            if desc_text:
                text += f"\n**Description**:\n{desc_text}\n"

        if project.get('createdAt'):
            text += f"\n**Created**: {project['createdAt']}\n"
        if project.get('updatedAt'):
            text += f"**Updated**: {project['updatedAt']}\n"

        return text

    except Exception as e:
        return f"❌ Failed to get project: {str(e)}"
