"""Weekly report generation tools."""

import json
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from src.server import mcp, get_client
from src.utils.formatting import format_success, format_error
from src.utils.report_formatter import (
    format_weekly_report_markdown,
    format_report_data_json,
)


class GenerateWeeklyReportInput(BaseModel):
    """Input model for generating weekly reports."""
    project_id: int = Field(..., description="Project ID to generate report for", gt=0)
    from_date: str = Field(..., description="Report start date (YYYY-MM-DD)")
    to_date: str = Field(..., description="Report end date (YYYY-MM-DD)")
    sprint_goal: Optional[str] = Field(None, description="Optional sprint goal text")
    team_name: Optional[str] = Field(None, description="Optional team/squad name")
    format: str = Field("markdown", description="Output format: 'markdown' or 'json'")


class GetReportDataInput(BaseModel):
    """Input model for getting raw report data."""
    project_id: int = Field(..., description="Project ID", gt=0)
    from_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    to_date: str = Field(..., description="End date (YYYY-MM-DD)")


@mcp.tool
async def generate_weekly_report(input: GenerateWeeklyReportInput) -> str:
    """Generate comprehensive weekly Agile/Scrum report automatically.
    
    This tool creates a full weekly report following the Agile/Scrum template with
    8 main sections:
    - A. General information (project, team, sprint)
    - B. Executive summary (progress, deliverables, blockers)
    - C. Delivery & backlog movement (done, in progress, planned)
    - D. Resources & capacity (team size, hours logged)
    - E. Impediments & dependencies (blockers, risks)
    - F. Quality & stability (bugs, incidents)
    - G. Next week plan (priorities)
    - H. Sprint health & improvements (retro signals)
    
    The tool automatically collects all necessary data from OpenProject including:
    - Project information
    - Work packages filtered by date range
    - Team members
    - Time entries for capacity tracking
    - Work package relations for dependencies
    
    Args:
        input: Report parameters including project_id, date range, and optional metadata
        
    Returns:
        Complete weekly report in markdown or JSON format
        
    Example:
        {
            "project_id": 5,
            "from_date": "2025-12-02",
            "to_date": "2025-12-08",
            "sprint_goal": "Complete user authentication feature",
            "team_name": "Backend Team Alpha",
            "format": "markdown"
        }
    """
    try:
        client = get_client()
        
        # Validate date format
        try:
            from_dt = datetime.strptime(input.from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(input.to_date, "%Y-%m-%d")
        except ValueError:
            return format_error("Invalid date format. Use YYYY-MM-DD")
        
        if from_dt > to_dt:
            return format_error("from_date must be before or equal to to_date")
        
        # Collect all data in parallel (async)
        # 1. Get project info
        project = await client.get_project(input.project_id)
        
        # 2. Get work packages updated within date range
        # Use filters to get work packages updated in the specified period
        filters = [
            {
                "updatedAt": {
                    "operator": "<>d",
                    "values": [input.from_date, input.to_date]
                }
            }
        ]
        filters_json = json.dumps(filters)
        
        wp_result = await client.get_work_packages(
            project_id=input.project_id,
            filters=filters_json,
            page_size=200  # Get more WPs for comprehensive report
        )
        work_packages = wp_result.get("_embedded", {}).get("elements", [])
        
        # 3. Get project members
        members_result = await client.get_memberships(project_id=input.project_id)
        members = members_result.get("_embedded", {}).get("elements", [])
        
        # 4. Get time entries within date range
        time_filters = json.dumps([
            {
                "spentOn": {
                    "operator": "<>d",
                    "values": [input.from_date, input.to_date]
                }
            },
            {
                "project": {
                    "operator": "=",
                    "values": [str(input.project_id)]
                }
            }
        ])
        
        te_result = await client.get_time_entries(filters=time_filters)
        time_entries = te_result.get("_embedded", {}).get("elements", [])
        
        # 5. Get relations for dependency analysis (optional, may not have many)
        relations = []
        try:
            # Get relations for all work packages (this might be slow for large projects)
            # For now, we'll collect relations from the first few WPs only
            for wp in work_packages[:10]:  # Limit to avoid too many API calls
                try:
                    rel_result = await client.get_relations(work_package_id=wp['id'])
                    wp_relations = rel_result.get("_embedded", {}).get("elements", [])
                    relations.extend(wp_relations)
                except:
                    pass  # Ignore if relations endpoint fails
        except:
            pass  # Relations are optional
        
        # Generate report based on format
        if input.format.lower() == 'json':
            # Return structured JSON data
            data = format_report_data_json(
                project=project,
                work_packages=work_packages,
                time_entries=time_entries,
                members=members,
                relations=relations
            )
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            # Return markdown report (default)
            report = format_weekly_report_markdown(
                project=project,
                work_packages=work_packages,
                time_entries=time_entries,
                members=members,
                from_date=input.from_date,
                to_date=input.to_date,
                sprint_goal=input.sprint_goal,
                team_name=input.team_name,
                relations=relations
            )
            
            return report
        
    except Exception as e:
        return format_error(f"Failed to generate weekly report: {str(e)}")


@mcp.tool
async def get_report_data(input: GetReportDataInput) -> str:
    """Get raw data for weekly report in JSON format for custom processing.
    
    This tool collects all the data needed for a weekly report but returns it
    as structured JSON instead of a formatted report. This allows you to:
    - Create custom report formats
    - Add additional analysis
    - Combine with other data sources
    - Build custom visualizations
    
    The returned data includes:
    - Project information
    - Work packages grouped by status (done, in_progress, planned, blocked, de_scoped)
    - Time entries with hours breakdown
    - Team members list
    - Calculated metrics (counts, hours, percentages)
    - Identified blockers
    
    Args:
        input: Project ID and date range
        
    Returns:
        JSON string with all report data structured for custom processing
        
    Example:
        {
            "project_id": 5,
            "from_date": "2025-12-02",
            "to_date": "2025-12-08"
        }
    """
    try:
        client = get_client()
        
        # Validate date format
        try:
            from_dt = datetime.strptime(input.from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(input.to_date, "%Y-%m-%d")
        except ValueError:
            return format_error("Invalid date format. Use YYYY-MM-DD")
        
        if from_dt > to_dt:
            return format_error("from_date must be before or equal to to_date")
        
        # Collect data
        project = await client.get_project(input.project_id)
        
        filters = [
            {
                "updatedAt": {
                    "operator": "<>d",
                    "values": [input.from_date, input.to_date]
                }
            }
        ]
        filters_json = json.dumps(filters)
        
        wp_result = await client.get_work_packages(
            project_id=input.project_id,
            filters=filters_json,
            page_size=200
        )
        work_packages = wp_result.get("_embedded", {}).get("elements", [])
        
        members_result = await client.get_memberships(project_id=input.project_id)
        members = members_result.get("_embedded", {}).get("elements", [])
        
        time_filters = json.dumps([
            {
                "spentOn": {
                    "operator": "<>d",
                    "values": [input.from_date, input.to_date]
                }
            },
            {
                "project": {
                    "operator": "=",
                    "values": [str(input.project_id)]
                }
            }
        ])
        
        te_result = await client.get_time_entries(filters=time_filters)
        time_entries = te_result.get("_embedded", {}).get("elements", [])
        
        # Format as JSON
        data = format_report_data_json(
            project=project,
            work_packages=work_packages,
            time_entries=time_entries,
            members=members
        )
        
        # Add metadata
        result = {
            "metadata": {
                "project_id": input.project_id,
                "from_date": input.from_date,
                "to_date": input.to_date,
                "generated_at": datetime.now().isoformat(),
                "work_packages_count": len(work_packages),
                "time_entries_count": len(time_entries),
                "members_count": len(members)
            },
            "data": data
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return format_error(f"Failed to get report data: {str(e)}")


@mcp.tool
async def generate_this_week_report(project_id: int, team_name: Optional[str] = None) -> str:
    """Quick shortcut to generate weekly report for the current week (Monday-Sunday).
    
    This is a convenience tool that automatically calculates the current week's
    date range and generates a report. It uses Monday as the start of the week.
    
    Args:
        project_id: Project ID to generate report for
        team_name: Optional team/squad name
        
    Returns:
        Complete weekly report in markdown format for the current week
        
    Example:
        {
            "project_id": 5,
            "team_name": "Backend Team"
        }
    """
    try:
        # Calculate current week (Monday to Sunday)
        today = datetime.now()
        
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        from_date = monday.strftime("%Y-%m-%d")
        
        # Get Sunday of current week
        sunday = monday + timedelta(days=6)
        to_date = sunday.strftime("%Y-%m-%d")
        
        # Generate report
        input_data = GenerateWeeklyReportInput(
            project_id=project_id,
            from_date=from_date,
            to_date=to_date,
            team_name=team_name,
            sprint_goal=None,
            format="markdown"
        )
        
        return await generate_weekly_report(input_data)
        
    except Exception as e:
        return format_error(f"Failed to generate this week's report: {str(e)}")


@mcp.tool
async def generate_last_week_report(project_id: int, team_name: Optional[str] = None) -> str:
    """Quick shortcut to generate weekly report for last week (Monday-Sunday).
    
    This is a convenience tool that automatically calculates last week's
    date range and generates a report.
    
    Args:
        project_id: Project ID to generate report for
        team_name: Optional team/squad name
        
    Returns:
        Complete weekly report in markdown format for last week
        
    Example:
        {
            "project_id": 5,
            "team_name": "Backend Team"
        }
    """
    try:
        # Calculate last week (Monday to Sunday)
        today = datetime.now()
        
        # Get Monday of last week
        last_monday = today - timedelta(days=today.weekday() + 7)
        from_date = last_monday.strftime("%Y-%m-%d")
        
        # Get Sunday of last week
        last_sunday = last_monday + timedelta(days=6)
        to_date = last_sunday.strftime("%Y-%m-%d")
        
        # Generate report
        input_data = GenerateWeeklyReportInput(
            project_id=project_id,
            from_date=from_date,
            to_date=to_date,
            team_name=team_name,
            sprint_goal=None,
            format="markdown"
        )
        
        return await generate_weekly_report(input_data)
        
    except Exception as e:
        return format_error(f"Failed to generate last week's report: {str(e)}")
