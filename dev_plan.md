cat > "C:\Users\haunt\.claude\plans\twinkly-dreaming-meteor-agent-dbed23f0.md" << 'PLAN_EOF'

# FastMCP Migration Plan for OpenProject MCP Server

**Status**: Planning Phase  
**Created**: 2025-12-02  
**Current Version**: 1.0.0 (Standard MCP SDK)  
**Target**: FastMCP-based implementation

---

## Executive Summary

This plan outlines the migration from the standard MCP SDK to FastMCP for the OpenProject MCP Server. The current implementation is a 3,213-line single-file application with 40 tools, suffering from significant code duplication (798 lines of manual tool definitions + 1,222 lines of elif dispatch logic). FastMCP will reduce this by ~60%, improve maintainability through decorators, add type safety, and provide better developer experience.

**Key Benefits**:

- **Code Reduction**: ~2,000 lines eliminated (manual schemas + dispatch logic)
- **Type Safety**: Automatic schema generation from type hints
- **Maintainability**: Decorator-based tools instead of giant elif blocks
- **Testing**: In-memory client for unit tests without subprocess overhead
- **Developer Experience**: Cleaner code, easier onboarding
- **Future-Proof**: Easier to add new tools and features

---

## 1. Architecture Design

### 1.1 Recommended Structure: **Hybrid Modular Approach**

**Decision**: Split into logical modules while maintaining simplicity for small teams.

```
openproject-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py              # FastMCP server initialization (50 lines)
│   ├── client.py              # OpenProjectClient (same, 1,100 lines)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── formatting.py      # Response formatters (150 lines)
│   │   ├── pagination.py      # Pagination helpers (50 lines)
│   │   └── errors.py          # Error handling utilities (50 lines)
│   └── tools/
│       ├── __init__.py
│       ├── connection.py      # test_connection, check_permissions (2 tools)
│       ├── projects.py        # Project management (5 tools)
│       ├── work_packages.py   # Work package CRUD + metadata (8 tools)
│       ├── hierarchy.py       # Parent-child relationships (3 tools)
│       ├── relations.py       # Work package relations (5 tools)
│       ├── users.py           # User & role management (6 tools)
│       ├── memberships.py     # Membership management (5 tools)
│       ├── time_entries.py    # Time tracking (5 tools)
│       └── versions.py        # Version management (2 tools)
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures
│   ├── test_connection.py
│   ├── test_projects.py
│   ├── test_work_packages.py
│   └── ...
├── openproject-mcp.py         # Entry point (backwards compatibility)
├── pyproject.toml
├── .env
└── README.md
```

**Rationale**:

- **Not single-file**: 3,213 lines is too large; hard to navigate
- **Not micro-services**: Overkill for 40 tools; increases complexity
- **Hybrid**: Groups related tools by domain (projects, work packages, etc.)
- **Entry point preserved**: `openproject-mcp.py` for Claude Desktop compatibility
- **Backward compatible**: Existing configs continue to work

### 1.2 OpenProjectClient Placement

**Decision**: Keep as standalone module (`src/client.py`)

**Rationale**:

- Unchanged architecture (still async aiohttp wrapper)
- Shared across all tool modules via dependency injection
- Easy to mock for testing
- No need to refactor (1,100 lines of working code)

**Access Pattern**:

```python
from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient

def get_client() -> OpenProjectClient:
    """Dependency that returns the global client instance."""
    return mcp.state.client

@mcp.tool
async def list_projects(
    active_only: bool = True,
    client: OpenProjectClient = Depends(get_client)
) -> str:
    """List all OpenProject projects."""
    # Use client...
```

### 1.3 Shared Utilities Organization

**Three utility modules**:

1. **formatting.py**: Response text builders

   - `format_project_list(projects: List[Dict]) -> str`
   - `format_work_package_detail(wp: Dict) -> str`
   - `format_success(message: str, details: Dict) -> str`
   - `format_error(message: str, exception: Exception) -> str`

2. **pagination.py**: Pagination logic

   - `build_pagination_filters(offset: int, page_size: int) -> str`
   - `format_pagination_info(result: Dict) -> str`

3. **errors.py**: Error handling
   - `handle_api_error(e: Exception) -> str`
   - Custom exception classes

---

## 2. Migration Strategy

### 2.1 Incremental Migration Approach

**Decision**: Gradual migration with parallel operation during transition.

**Phases**:

#### Phase 0: Preparation (1-2 hours)

1. Install FastMCP: `uv add fastmcp`
2. Create directory structure (`src/`, `src/tools/`, `src/utils/`)
3. Set up test infrastructure (`tests/conftest.py`)
4. Create shared utilities (formatters, pagination, errors)

#### Phase 1: Proof of Concept (2-4 hours)

**Migrate 2 simple tools to validate approach**:

- `test_connection` (simplest, no arguments)
- `list_projects` (simple filter, pagination)

**Validation**:

- Tools callable via in-memory client
- Response format matches original
- Environment variables working
- Claude Desktop integration functional

#### Phase 2: Core Tools (6-8 hours)

**Migrate by category in dependency order**:

1. Connection tools (2) - `connection.py`
2. Project tools (5) - `projects.py`
3. Work package CRUD (8) - `work_packages.py`
4. Users & Roles (6) - `users.py`

**Parallel Testing**: Run both old and new implementations side-by-side.

#### Phase 3: Advanced Features (6-8 hours)

1. Hierarchy tools (3) - `hierarchy.py`
2. Relations tools (5) - `relations.py`
3. Membership tools (5) - `memberships.py`
4. Time entries (5) - `time_entries.py`
5. Versions (2) - `versions.py`

#### Phase 4: Testing & Refinement (4-6 hours)

1. Comprehensive integration tests
2. Documentation updates
3. Migration guide for contributors
4. Performance comparison

#### Phase 5: Cutover (1 hour)

1. Update `openproject-mcp.py` to use new FastMCP server
2. Archive old implementation as `openproject-mcp.legacy.py`
3. Update Claude Desktop config (if needed)
4. Final validation

**Total Estimated Time**: 20-30 hours of development

### 2.2 Backwards Compatibility Strategy

**During Migration**:

- Keep `openproject-mcp.py` working with old code
- Run both versions in parallel for validation
- Use feature flags if needed

**After Migration**:

- `openproject-mcp.py` imports and runs FastMCP server
- Same Claude Desktop config (no user changes required)
- Same environment variables (`.env` unchanged)

---

## 3. FastMCP Implementation Details

### 3.1 Server Initialization Pattern

**File**: `src/server.py`

```python
import os
from fastmcp import FastMCP
from dotenv import load_dotenv
from src.client import OpenProjectClient

# Load environment variables
load_dotenv()

# Create FastMCP server
mcp = FastMCP(
    name="openproject-mcp",
    version="2.0.0",
    description="OpenProject API v3 integration via MCP"
)

# Initialize OpenProject client and store in server state
def initialize_client():
    """Initialize OpenProject client from environment variables."""
    base_url = os.getenv("OPENPROJECT_URL")
    api_key = os.getenv("OPENPROJECT_API_KEY")
    proxy = os.getenv("OPENPROJECT_PROXY")

    if not base_url or not api_key:
        raise ValueError(
            "OPENPROJECT_URL and OPENPROJECT_API_KEY must be set in .env file"
        )

    return OpenProjectClient(base_url, api_key, proxy)

# Store client in server state for dependency injection
mcp.state.client = initialize_client()

# Import tool modules to register decorators
from src.tools import (
    connection,
    projects,
    work_packages,
    hierarchy,
    relations,
    users,
    memberships,
    time_entries,
    versions
)
```

### 3.2 Tool Definition Pattern (Decorator-Based)

**Example 1: Simple Tool (No Context)**

**File**: `src/tools/connection.py`

```python
from fastmcp import FastMCP
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient
from src.server import mcp

def get_client() -> OpenProjectClient:
    return mcp.state.client

@mcp.tool
async def test_connection(
    client: OpenProjectClient = Depends(get_client)
) -> str:
    """Test the connection to the OpenProject API.

    Returns:
        Connection status and instance information.
    """
    try:
        result = await client.test_connection()

        text = "✅ API connection successful!\n\n"
        if client.proxy:
            text += f"Connected via proxy: {client.proxy}\n"
        text += f"API Version: {result.get('_type', 'Unknown')}\n"
        text += f"Instance Version: {result.get('instanceVersion', 'Unknown')}\n"

        return text
    except Exception as e:
        return f"❌ Connection failed: {str(e)}"
```

**Example 2: Tool with Context (Logging)**

**File**: `src/tools/projects.py`

```python
from typing import Optional
from fastmcp import Context
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient
from src.server import mcp
from src.utils.formatting import format_project_list, format_error
import json

def get_client() -> OpenProjectClient:
    return mcp.state.client

@mcp.tool
async def list_projects(
    active_only: bool = True,
    ctx: Context = None,
    client: OpenProjectClient = Depends(get_client)
) -> str:
    """List all OpenProject projects.

    Args:
        active_only: Show only active projects (default: True)

    Returns:
        Formatted list of projects with details.
    """
    try:
        if ctx:
            await ctx.info(f"Fetching projects (active_only={active_only})")

        filters = None
        if active_only:
            filters = json.dumps([{"active": {"operator": "=", "values": ["t"]}}])

        result = await client.get_projects(filters)
        projects = result.get("_embedded", {}).get("elements", [])

        if ctx:
            await ctx.info(f"Found {len(projects)} projects")

        return format_project_list(projects)

    except Exception as e:
        if ctx:
            await ctx.error(f"Failed to list projects: {str(e)}")
        return format_error("listing projects", e)
```

**Example 3: Complex Tool with Pagination**

**File**: `src/tools/work_packages.py`

```python
from typing import Optional, Literal
from fastmcp import Context
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient
from src.server import mcp
from src.utils.formatting import format_work_package_list
from src.utils.pagination import build_pagination_filters
import json

def get_client() -> OpenProjectClient:
    return mcp.state.client

@mcp.tool
async def list_work_packages(
    project_id: Optional[int] = None,
    status: Literal["open", "closed", "all"] = "open",
    offset: Optional[int] = None,
    page_size: Optional[int] = None,
    ctx: Context = None,
    client: OpenProjectClient = Depends(get_client)
) -> str:
    """List work packages with optional filtering and pagination.

    Args:
        project_id: Filter by specific project ID
        status: Filter by status - "open", "closed", or "all" (default: "open")
        offset: Starting index for pagination (default: 1)
        page_size: Number of results per page (max: 100)

    Returns:
        Formatted list of work packages with pagination info.
    """
    try:
        if ctx:
            log_msg = f"Fetching work packages (status={status}"
            if project_id:
                log_msg += f", project_id={project_id}"
            if offset or page_size:
                log_msg += f", offset={offset}, page_size={page_size}"
            log_msg += ")"
            await ctx.info(log_msg)

        # Build filters
        filters = None
        if status == "open":
            filters = json.dumps([{"status_id": {"operator": "o", "values": None}}])
        elif status == "closed":
            filters = json.dumps([{"status_id": {"operator": "c", "values": None}}])

        result = await client.get_work_packages(
            project_id, filters, offset, page_size
        )
        work_packages = result.get("_embedded", {}).get("elements", [])

        if ctx:
            total = result.get("total", len(work_packages))
            await ctx.info(f"Found {total} work packages (showing {len(work_packages)})")

        return format_work_package_list(result)

    except Exception as e:
        if ctx:
            await ctx.error(f"Failed to list work packages: {str(e)}")
        return f"❌ Error listing work packages: {str(e)}"
```

**Example 4: Tool with Complex Arguments**

**File**: `src/tools/work_packages.py`

```python
from typing import Optional
from pydantic import BaseModel, Field
from fastmcp import Context
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient
from src.server import mcp
import json

def get_client() -> OpenProjectClient:
    return mcp.state.client

# Pydantic model for complex input validation
class CreateWorkPackageInput(BaseModel):
    project_id: int = Field(..., description="Project ID")
    subject: str = Field(..., description="Work package title")
    type_id: int = Field(..., description="Type ID (e.g., 1 for Task)")
    description: Optional[str] = Field(None, description="Description (Markdown supported)")
    priority_id: Optional[int] = Field(None, description="Priority ID")
    assignee_id: Optional[int] = Field(None, description="Assignee user ID")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")
    date: Optional[str] = Field(None, description="Date for milestones (YYYY-MM-DD)")

@mcp.tool
async def create_work_package(
    input: CreateWorkPackageInput,
    ctx: Context = None,
    client: OpenProjectClient = Depends(get_client)
) -> str:
    """Create a new work package with optional date fields.

    Args:
        input: Work package creation parameters

    Returns:
        Created work package details.
    """
    try:
        if ctx:
            await ctx.info(f"Creating work package: {input.subject}")

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

        # Add date fields
        if input.start_date:
            data["startDate"] = input.start_date
        if input.due_date:
            data["dueDate"] = input.due_date
        if input.date:
            data["date"] = input.date

        result = await client.create_work_package(data)

        if ctx:
            await ctx.info(f"Created work package #{result.get('id')}")

        text = f"✅ Work package created successfully:\n\n"
        text += f"- **Title**: {result.get('subject', 'N/A')}\n"
        text += f"- **ID**: #{result.get('id', 'N/A')}\n"
        # ... more formatting

        return text

    except Exception as e:
        if ctx:
            await ctx.error(f"Failed to create work package: {str(e)}")
        return f"❌ Error creating work package: {str(e)}"
```

### 3.3 Type Hints for All 40 Tools

**Strategy**: Use Python type hints + Pydantic models for complex inputs

**Benefits**:

- FastMCP auto-generates JSON schemas
- Client-side validation
- Better IDE autocomplete
- Self-documenting code

**Pattern**:

```python
# Simple args: use function parameters with defaults
@mcp.tool
async def get_user(user_id: int) -> str:
    """Get user details."""
    pass

# Complex args: use Pydantic BaseModel
class UpdateWorkPackageInput(BaseModel):
    work_package_id: int
    subject: Optional[str] = None
    description: Optional[str] = None
    # ... 10+ optional fields

@mcp.tool
async def update_work_package(input: UpdateWorkPackageInput) -> str:
    """Update work package."""
    pass
```

### 3.4 Response Formatting Patterns

**Shared Formatter Functions** (`src/utils/formatting.py`):

```python
from typing import List, Dict

def format_success(title: str, details: Dict[str, Any]) -> str:
    """Format a success response with details."""
    text = f"✅ {title}\n\n"
    for key, value in details.items():
        text += f"- **{key}**: {value}\n"
    return text

def format_error(action: str, exception: Exception) -> str:
    """Format an error response."""
    return f"❌ Error {action}: {str(exception)}"

def format_project_list(projects: List[Dict]) -> str:
    """Format a list of projects."""
    if not projects:
        return "No projects found."

    text = f"Found {len(projects)} project(s):\n\n"
    for project in projects:
        text += f"- **{project['name']}** (ID: {project['id']})\n"
        if project.get("description", {}).get("raw"):
            text += f"  {project['description']['raw']}\n"
        text += f"  Status: {'Active' if project.get('active') else 'Inactive'}\n"
        text += f"  Public: {'Yes' if project.get('public') else 'No'}\n\n"

    return text

def format_work_package_list(result: Dict) -> str:
    """Format work packages with pagination info."""
    work_packages = result.get("_embedded", {}).get("elements", [])
    total = result.get("total", len(work_packages))
    count = result.get("count", len(work_packages))
    offset = result.get("offset", 1)
    page_size = result.get("pageSize", 20)

    if not work_packages:
        return "No work packages found."

    text = f"Found {total} work package(s) (showing {count} results, "
    text += f"offset: {offset}, pageSize: {page_size}):\n\n"

    for wp in work_packages:
        text += f"- **{wp.get('subject', 'No title')}** (#{wp.get('id', 'N/A')})\n"

        if "_embedded" in wp:
            embedded = wp["_embedded"]
            if "type" in embedded:
                text += f"  Type: {embedded['type'].get('name', 'Unknown')}\n"
            if "status" in embedded:
                text += f"  Status: {embedded['status'].get('name', 'Unknown')}\n"
            if "project" in embedded:
                text += f"  Project: {embedded['project'].get('name', 'Unknown')}\n"
            if "assignee" in embedded and embedded["assignee"]:
                text += f"  Assignee: {embedded['assignee'].get('name', 'Unassigned')}\n"

        if "percentageDone" in wp:
            text += f"  Progress: {wp['percentageDone']}%\n"

        text += "\n"

    return text
```

### 3.5 Context Parameter Usage

**When to use Context**:

1. **Logging**: Progress updates, debugging info
2. **Long-running operations**: Progress reporting
3. **Resource access**: Reading server resources
4. **LLM interaction**: Asking client LLM for help (advanced)

**Pattern**:

```python
@mcp.tool
async def complex_operation(
    data: str,
    ctx: Context = None  # Optional, defaults to None
) -> str:
    """Perform a complex operation with progress tracking."""
    if ctx:
        await ctx.info("Starting operation")
        await ctx.report_progress(progress=0, total=100)

    # Step 1
    result1 = await do_step_1(data)
    if ctx:
        await ctx.report_progress(progress=33, total=100)

    # Step 2
    result2 = await do_step_2(result1)
    if ctx:
        await ctx.report_progress(progress=66, total=100)

    # Step 3
    final = await do_step_3(result2)
    if ctx:
        await ctx.info("Operation complete")
        await ctx.report_progress(progress=100, total=100)

    return final
```

**Recommendation**: Use Context for:

- All `create_*` tools (log creation events)
- All `update_*` and `delete_*` tools (audit trail)
- `list_*` tools with pagination (show progress)
- Complex multi-step operations

---

## 4. Testing & Validation

### 4.1 Testing Strategy

**In-Memory Testing** (FastMCP advantage):

```python
# tests/conftest.py
import pytest
from fastmcp import Client
from src.server import mcp

@pytest.fixture
async def client():
    """Provide an in-memory FastMCP client for testing."""
    async with Client(mcp) as client:
        yield client

@pytest.fixture
def mock_openproject_client(mocker):
    """Mock the OpenProjectClient for unit tests."""
    return mocker.patch("src.server.mcp.state.client")
```

**Example Unit Test**:

```python
# tests/test_connection.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_connection_success(client, mock_openproject_client):
    """Test successful connection."""
    # Mock the API response
    mock_openproject_client.test_connection.return_value = {
        "_type": "Root",
        "instanceVersion": "12.5.0"
    }
    mock_openproject_client.proxy = None

    # Call the tool
    result = await client.call_tool("test_connection", {})

    # Verify
    assert "✅ API connection successful!" in result.data
    assert "Instance Version: 12.5.0" in result.data
    mock_openproject_client.test_connection.assert_called_once()

@pytest.mark.asyncio
async def test_connection_failure(client, mock_openproject_client):
    """Test connection failure."""
    # Mock an exception
    mock_openproject_client.test_connection.side_effect = Exception("Network error")

    # Call the tool
    result = await client.call_tool("test_connection", {})

    # Verify error handling
    assert "❌ Connection failed" in result.data
    assert "Network error" in result.data
```

**Example Integration Test**:

```python
# tests/test_projects_integration.py
import pytest
import os
from fastmcp import Client
from src.server import mcp

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENPROJECT_URL"),
    reason="Integration tests require OPENPROJECT_URL"
)
@pytest.mark.asyncio
async def test_list_projects_real_api():
    """Test list_projects against real OpenProject instance."""
    async with Client(mcp) as client:
        result = await client.call_tool("list_projects", {"active_only": True})

        # Verify response format
        assert "project(s):" in result.data or "No projects found" in result.data
```

### 4.2 Validation During Migration

**Parallel Testing Approach**:

```python
# tests/test_migration_parity.py
import pytest
from src.server import mcp as new_mcp
from openproject_mcp_legacy import OpenProjectMCPServer as OldServer

@pytest.mark.asyncio
async def test_list_projects_parity(mock_openproject_client):
    """Ensure new implementation matches old behavior."""
    # Setup
    mock_data = {
        "_embedded": {
            "elements": [
                {"id": 1, "name": "Test Project", "active": True}
            ]
        }
    }
    mock_openproject_client.get_projects.return_value = mock_data

    # New implementation
    from fastmcp import Client
    async with Client(new_mcp) as client:
        new_result = await client.call_tool("list_projects", {"active_only": True})

    # Old implementation (convert to callable format)
    old_server = OldServer()
    old_server.client = mock_openproject_client
    old_result = await old_server.call_tool("list_projects", {"active_only": True})

    # Compare
    assert new_result.data == old_result[0].text
```

### 4.3 Integration Testing Approach

**Test Pyramid**:

- **Unit Tests** (70%): Mock OpenProjectClient, test tool logic
- **Integration Tests** (20%): Real API calls (optional, requires test instance)
- **End-to-End Tests** (10%): Full Claude Desktop workflow

**CI/CD Pipeline**:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync --extra dev
      - name: Run unit tests
        run: uv run pytest tests/ -m "not integration"
      - name: Run integration tests (if secrets available)
        if: ${{ secrets.OPENPROJECT_URL }}
        env:
          OPENPROJECT_URL: ${{ secrets.OPENPROJECT_URL }}
          OPENPROJECT_API_KEY: ${{ secrets.OPENPROJECT_API_KEY }}
        run: uv run pytest tests/ -m integration
```

---

## 5. Deployment & Configuration

### 5.1 Changes Needed for Claude Desktop Integration

**Good News**: Minimal changes required!

**Current Config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "openproject": {
      "command": "d:/Promete/Project/mcp-openproject/openproject-mcp-server/.venv/Scripts/python.exe",
      "args": [
        "d:/Promete/Project/mcp-openproject/openproject-mcp-server/openproject-mcp.py"
      ]
    }
  }
}
```

**New Config** (unchanged!):

```json
{
  "mcpServers": {
    "openproject": {
      "command": "d:/Promete/Project/mcp-openproject/openproject-mcp-server/.venv/Scripts/python.exe",
      "args": [
        "d:/Promete/Project/mcp-openproject/openproject-mcp-server/openproject-mcp.py"
      ]
    }
  }
}
```

**Entry Point** (`openproject-mcp.py` - new version):

```python
#!/usr/bin/env python3
"""
OpenProject MCP Server - Entry Point
Runs the FastMCP-based server for Claude Desktop integration.
"""

import asyncio
from src.server import mcp

if __name__ == "__main__":
    # Run with default STDIO transport
    mcp.run()  # FastMCP handles stdio_server internally
```

**Alternative with Logging**:

```python
#!/usr/bin/env python3
import asyncio
import logging
from src.server import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    logging.info("Starting OpenProject MCP Server v2.0.0")
    mcp.run()  # Uses STDIO by default
```

### 5.2 Environment Variable Handling

**No Changes Required**:

- `.env` file format stays the same
- `python-dotenv` still used
- Same variables: `OPENPROJECT_URL`, `OPENPROJECT_API_KEY`, `OPENPROJECT_PROXY`, `LOG_LEVEL`

**Implementation** (`src/server.py`):

```python
import os
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()  # Load .env file

# Validate required variables
required_vars = ["OPENPROJECT_URL", "OPENPROJECT_API_KEY"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Initialize client
from src.client import OpenProjectClient
mcp.state.client = OpenProjectClient(
    base_url=os.getenv("OPENPROJECT_URL"),
    api_key=os.getenv("OPENPROJECT_API_KEY"),
    proxy=os.getenv("OPENPROJECT_PROXY")
)
```

### 5.3 Docker Support

**Current Docker Support**: The project has Docker capability (per CLAUDE.md).

**Updated Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY openproject-mcp.py ./

# Install dependencies
RUN uv sync

# Set environment variable defaults
ENV OPENPROJECT_URL=""
ENV OPENPROJECT_API_KEY=""
ENV OPENPROJECT_PROXY=""
ENV LOG_LEVEL="INFO"

# Run the server
CMD ["uv", "run", "python", "openproject-mcp.py"]
```

**Updated docker-compose.yml**:

```yaml
version: "3.8"

services:
  openproject-mcp:
    build: .
    env_file:
      - .env
    stdin_open: true # Required for STDIO transport
    tty: true
    volumes:
      - ./logs:/app/logs # Optional: persist logs
```

**HTTP Transport (Alternative for Web Access)**:

**File**: `openproject-mcp-http.py`

```python
#!/usr/bin/env python3
"""
OpenProject MCP Server - HTTP Transport
For web-based or remote access.
"""

from src.server import mcp

if __name__ == "__main__":
    # Run with HTTP transport
    mcp.run(transport="http", port=8000)
```

**Docker Compose for HTTP**:

```yaml
services:
  openproject-mcp-http:
    build: .
    command: ["uv", "run", "python", "openproject-mcp-http.py"]
    ports:
      - "8000:8000"
    env_file:
      - .env
```

---

## 6. Code Organization Examples

### 6.1 Complete Tool Module Example

**File**: `src/tools/connection.py`

```python
"""
Connection and permission testing tools.

Tools:
- test_connection: Test API connectivity
- check_permissions: Verify user permissions
"""

from fastmcp import Context
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient
from src.server import mcp

def get_client() -> OpenProjectClient:
    """Dependency injection for OpenProjectClient."""
    return mcp.state.client


@mcp.tool
async def test_connection(
    client: OpenProjectClient = Depends(get_client),
    ctx: Context = None
) -> str:
    """Test the connection to the OpenProject API.

    Verifies that the API URL, API key, and network connectivity are working.
    Reports the OpenProject instance version if successful.

    Returns:
        Connection status and instance information.
    """
    try:
        if ctx:
            await ctx.info("Testing API connection...")

        result = await client.test_connection()

        text = "✅ API connection successful!\n\n"
        if client.proxy:
            text += f"Connected via proxy: {client.proxy}\n"
        text += f"API Version: {result.get('_type', 'Unknown')}\n"
        text += f"Instance Version: {result.get('instanceVersion', 'Unknown')}\n"

        if ctx:
            await ctx.info("Connection test successful")

        return text

    except Exception as e:
        if ctx:
            await ctx.error(f"Connection test failed: {str(e)}")
        return f"❌ Connection failed: {str(e)}"


@mcp.tool
async def check_permissions(
    client: OpenProjectClient = Depends(get_client),
    ctx: Context = None
) -> str:
    """Check user permissions in the OpenProject instance.

    Retrieves and displays the current user's global and project permissions.
    Useful for diagnosing permission-related issues.

    Returns:
        Current user information and permissions.
    """
    try:
        if ctx:
            await ctx.info("Checking user permissions...")

        # Get current user info (uses /api/v3/users/me endpoint)
        user_info = await client._request("GET", "/users/me")

        text = "**Current User Permissions:**\n\n"
        text += f"- **User**: {user_info.get('name', 'Unknown')}\n"
        text += f"- **Email**: {user_info.get('email', 'N/A')}\n"
        text += f"- **Admin**: {'Yes' if user_info.get('admin') else 'No'}\n"
        text += f"- **Status**: {user_info.get('status', 'Unknown')}\n\n"

        # Get global permissions
        if "_links" in user_info and "memberships" in user_info["_links"]:
            text += "**Global Permissions**: Available via memberships\n"
        else:
            text += "**Global Permissions**: Limited (non-admin user)\n"

        text += "\n**Note**: Use `list_memberships` to see project-specific permissions.\n"

        if ctx:
            await ctx.info("Permission check complete")

        return text

    except Exception as e:
        if ctx:
            await ctx.error(f"Permission check failed: {str(e)}")
        return f"❌ Error checking permissions: {str(e)}"
```

### 6.2 Shared Utility Example

**File**: `src/utils/formatting.py`

```python
"""
Response formatting utilities for consistent output across all tools.
"""

from typing import List, Dict, Any, Optional


def format_success(title: str, details: Dict[str, Any]) -> str:
    """Format a success response with structured details.

    Args:
        title: Success message title
        details: Dictionary of key-value pairs to display

    Returns:
        Formatted success message
    """
    text = f"✅ {title}\n\n"
    for key, value in details.items():
        # Convert key from snake_case to Title Case
        display_key = key.replace("_", " ").title()
        text += f"- **{display_key}**: {value}\n"
    return text


def format_error(action: str, exception: Exception) -> str:
    """Format an error response consistently.

    Args:
        action: Description of what was being attempted
        exception: The exception that occurred

    Returns:
        Formatted error message
    """
    return f"❌ Error {action}: {str(exception)}"


def format_project_list(projects: List[Dict]) -> str:
    """Format a list of projects for display.

    Args:
        projects: List of project dictionaries from OpenProject API

    Returns:
        Formatted project list
    """
    if not projects:
        return "No projects found."

    text = f"Found {len(projects)} project(s):\n\n"
    for project in projects:
        text += f"- **{project['name']}** (ID: {project['id']})\n"

        # Description (if present)
        if project.get("description", {}).get("raw"):
            desc = project['description']['raw']
            # Truncate long descriptions
            if len(desc) > 100:
                desc = desc[:100] + "..."
            text += f"  {desc}\n"

        # Status and visibility
        text += f"  Status: {'Active' if project.get('active') else 'Inactive'}\n"
        text += f"  Public: {'Yes' if project.get('public') else 'No'}\n"

        # Identifier
        if project.get("identifier"):
            text += f"  Identifier: {project['identifier']}\n"

        text += "\n"

    return text


def format_work_package_list(result: Dict) -> str:
    """Format work packages with pagination information.

    Args:
        result: Full API response including _embedded.elements and pagination

    Returns:
        Formatted work package list with pagination info
    """
    work_packages = result.get("_embedded", {}).get("elements", [])
    total = result.get("total", len(work_packages))
    count = result.get("count", len(work_packages))
    offset = result.get("offset", 1)
    page_size = result.get("pageSize", 20)

    if not work_packages:
        return "No work packages found."

    # Header with pagination info
    text = f"Found {total} work package(s) "
    text += f"(showing {count} results, offset: {offset}, pageSize: {page_size}):\n\n"

    # Work package details
    for wp in work_packages:
        text += f"- **{wp.get('subject', 'No title')}** (#{wp.get('id', 'N/A')})\n"

        # Embedded data
        if "_embedded" in wp:
            embedded = wp["_embedded"]

            if "type" in embedded:
                text += f"  Type: {embedded['type'].get('name', 'Unknown')}\n"

            if "status" in embedded:
                text += f"  Status: {embedded['status'].get('name', 'Unknown')}\n"

            if "project" in embedded:
                text += f"  Project: {embedded['project'].get('name', 'Unknown')}\n"

            if "assignee" in embedded:
                if embedded["assignee"]:
                    text += f"  Assignee: {embedded['assignee'].get('name', 'Unassigned')}\n"
                else:
                    text += f"  Assignee: Unassigned\n"

            if "priority" in embedded:
                text += f"  Priority: {embedded['priority'].get('name', 'Normal')}\n"

        # Progress
        if "percentageDone" in wp:
            text += f"  Progress: {wp['percentageDone']}%\n"

        # Dates
        if wp.get("startDate"):
            text += f"  Start: {wp['startDate']}\n"
        if wp.get("dueDate"):
            text += f"  Due: {wp['dueDate']}\n"

        text += "\n"

    # Pagination hint
    if total > count + offset - 1:
        remaining = total - (count + offset - 1)
        text += f"\n**Note**: {remaining} more work packages available. "
        text += f"Use `offset={offset + page_size}` to see next page.\n"

    return text


def format_work_package_detail(wp: Dict) -> str:
    """Format detailed work package information.

    Args:
        wp: Work package dictionary from OpenProject API

    Returns:
        Formatted work package details
    """
    text = f"**Work Package Details:**\n\n"
    text += f"- **ID**: #{wp.get('id', 'N/A')}\n"
    text += f"- **Subject**: {wp.get('subject', 'No subject')}\n"

    # Description
    if wp.get("description", {}).get("raw"):
        text += f"- **Description**:\n  {wp['description']['raw']}\n"

    # Type, status, priority from embedded data
    if "_embedded" in wp:
        embedded = wp["_embedded"]

        if "type" in embedded:
            text += f"- **Type**: {embedded['type'].get('name', 'Unknown')}\n"
        if "status" in embedded:
            text += f"- **Status**: {embedded['status'].get('name', 'Unknown')}\n"
        if "priority" in embedded:
            text += f"- **Priority**: {embedded['priority'].get('name', 'Unknown')}\n"
        if "project" in embedded:
            text += f"- **Project**: {embedded['project'].get('name', 'Unknown')} (ID: {embedded['project'].get('id')})\n"
        if "assignee" in embedded and embedded["assignee"]:
            text += f"- **Assignee**: {embedded['assignee'].get('name', 'Unassigned')}\n"

    # Progress and dates
    if "percentageDone" in wp:
        text += f"- **Progress**: {wp['percentageDone']}%\n"
    if wp.get("startDate"):
        text += f"- **Start Date**: {wp['startDate']}\n"
    if wp.get("dueDate"):
        text += f"- **Due Date**: {wp['dueDate']}\n"
    if wp.get("estimatedTime"):
        text += f"- **Estimated Time**: {wp['estimatedTime']}\n"

    # Metadata
    if wp.get("createdAt"):
        text += f"- **Created**: {wp['createdAt']}\n"
    if wp.get("updatedAt"):
        text += f"- **Updated**: {wp['updatedAt']}\n"

    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text with "..." if over max_length
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
```

### 6.3 Context Usage Example (Advanced)

**File**: `src/tools/work_packages.py`

```python
from fastmcp import Context
from fastmcp.server.dependencies import Depends
from src.client import OpenProjectClient
from src.server import mcp
from src.utils.formatting import format_work_package_detail, format_error

@mcp.tool
async def create_work_package_with_subtasks(
    parent_subject: str,
    parent_type_id: int,
    project_id: int,
    subtask_subjects: List[str],
    ctx: Context = None,
    client: OpenProjectClient = Depends(get_client)
) -> str:
    """Create a parent work package with multiple subtasks.

    This is a convenience tool for creating a work package hierarchy in one call.

    Args:
        parent_subject: Title of the parent work package
        parent_type_id: Type ID for parent (e.g., 1 for Epic)
        project_id: Project ID
        subtask_subjects: List of subtask titles to create

    Returns:
        Summary of created work packages.
    """
    try:
        total_steps = 1 + len(subtask_subjects)
        current_step = 0

        # Step 1: Create parent
        if ctx:
            await ctx.info(f"Creating parent work package: {parent_subject}")
            await ctx.report_progress(progress=current_step, total=total_steps)

        parent_data = {
            "project": project_id,
            "subject": parent_subject,
            "type": parent_type_id
        }
        parent = await client.create_work_package(parent_data)
        parent_id = parent.get("id")

        current_step += 1
        if ctx:
            await ctx.info(f"Created parent work package #{parent_id}")
            await ctx.report_progress(progress=current_step, total=total_steps)

        # Step 2: Create subtasks
        subtasks_created = []
        for i, subtask_subject in enumerate(subtask_subjects, 1):
            if ctx:
                await ctx.info(f"Creating subtask {i}/{len(subtask_subjects)}: {subtask_subject}")

            subtask_data = {
                "project": project_id,
                "subject": subtask_subject,
                "type": parent_type_id  # Same type as parent
            }
            subtask = await client.create_work_package(subtask_data)
            subtask_id = subtask.get("id")

            # Set parent relationship
            await client.set_work_package_parent(subtask_id, parent_id)

            subtasks_created.append(subtask_id)
            current_step += 1

            if ctx:
                await ctx.info(f"Created and linked subtask #{subtask_id}")
                await ctx.report_progress(progress=current_step, total=total_steps)

        # Summary
        text = f"✅ Created work package hierarchy:\n\n"
        text += f"**Parent**: #{parent_id} - {parent_subject}\n"
        text += f"**Subtasks**: {len(subtasks_created)} created\n\n"

        for i, subtask_id in enumerate(subtasks_created, 1):
            text += f"  {i}. #{subtask_id} - {subtask_subjects[i-1]}\n"

        if ctx:
            await ctx.info("Hierarchy creation complete")

        return text

    except Exception as e:
        if ctx:
            await ctx.error(f"Failed to create hierarchy: {str(e)}")
        return format_error("creating work package hierarchy", e)
```

---

## 7. Migration Checklist

### Phase 0: Preparation

- [ ] Install FastMCP: `uv add fastmcp`
- [ ] Create directory structure (`src/`, `src/tools/`, `src/utils/`, `tests/`)
- [ ] Copy `OpenProjectClient` to `src/client.py` (unchanged)
- [ ] Create `src/server.py` with FastMCP initialization
- [ ] Create shared utilities (`src/utils/formatting.py`, `src/utils/pagination.py`, `src/utils/errors.py`)
- [ ] Set up test infrastructure (`tests/conftest.py`)

### Phase 1: Proof of Concept (2 tools)

- [ ] Migrate `test_connection` to `src/tools/connection.py`
- [ ] Migrate `list_projects` to `src/tools/projects.py`
- [ ] Write unit tests for both tools
- [ ] Test in-memory client
- [ ] Test with Claude Desktop (update entry point)
- [ ] Validate response format matches original

### Phase 2: Core Tools (19 tools)

- [ ] Connection tools (2): `test_connection`, `check_permissions`
- [ ] Project tools (5): `list_projects`, `get_project`, `create_project`, `update_project`, `delete_project`
- [ ] Work package CRUD (8): `list_work_packages`, `get_work_package`, `create_work_package`, `update_work_package`, `delete_work_package`, `list_types`, `list_statuses`, `list_priorities`
- [ ] User tools (4): `list_users`, `get_user`, `list_roles`, `get_role`
- [ ] Write unit tests for all tools
- [ ] Write integration tests for critical paths
- [ ] Parallel testing with old implementation

### Phase 3: Advanced Features (21 tools)

- [ ] Hierarchy tools (3): `set_work_package_parent`, `remove_work_package_parent`, `list_work_package_children`
- [ ] Relations tools (5): `create_work_package_relation`, `list_work_package_relations`, `get_work_package_relation`, `update_work_package_relation`, `delete_work_package_relation`
- [ ] Membership tools (5): `list_memberships`, `get_membership`, `create_membership`, `update_membership`, `delete_membership`
- [ ] User-project tools (2): `list_project_members`, `list_user_projects`
- [ ] Time entry tools (5): `list_time_entries`, `create_time_entry`, `update_time_entry`, `delete_time_entry`, `list_time_entry_activities`
- [ ] Version tools (2): `list_versions`, `create_version`
- [ ] Write unit tests for all tools
- [ ] Write integration tests for complex workflows

### Phase 4: Testing & Refinement

- [ ] Run full test suite (unit + integration)
- [ ] Performance comparison (old vs new)
- [ ] Memory usage comparison
- [ ] End-to-end testing with Claude Desktop
- [ ] Test all 40 tools manually
- [ ] Fix any regressions
- [ ] Update documentation (README.md, CLAUDE.md)
- [ ] Create migration guide for contributors
- [ ] Update Docker configuration

### Phase 5: Cutover

- [ ] Archive old implementation as `openproject-mcp.legacy.py`
- [ ] Update `openproject-mcp.py` to use FastMCP server
- [ ] Update `pyproject.toml` dependencies
- [ ] Test Claude Desktop integration
- [ ] Run final validation
- [ ] Create release notes
- [ ] Tag release (v2.0.0)

### Post-Migration

- [ ] Monitor for issues
- [ ] Collect feedback from team
- [ ] Optimize based on usage patterns
- [ ] Consider additional FastMCP features (resources, prompts)

---

## 8. Risk Assessment & Mitigation

### High-Risk Areas

**Risk 1: Breaking Claude Desktop Integration**

- **Impact**: High (users can't use the server)
- **Mitigation**: Keep entry point (`openproject-mcp.py`) unchanged, extensive testing
- **Rollback**: Keep old implementation available

**Risk 2: Changing Response Formats**

- **Impact**: Medium (LLM may parse differently)
- **Mitigation**: Parallel testing, format validation tests
- **Rollback**: Easy (adjust formatters)

**Risk 3: Missing Tool Functionality**

- **Impact**: High (loss of features)
- **Mitigation**: Comprehensive test coverage, parity testing
- **Rollback**: Use old implementation for missing tools

**Risk 4: Performance Degradation**

- **Impact**: Medium (slower responses)
- **Mitigation**: Performance benchmarks, async/await patterns
- **Rollback**: Optimize or revert

### Low-Risk Areas

- **Type Safety**: FastMCP adds validation, reduces errors
- **Testing**: In-memory client makes tests easier and faster
- **Maintainability**: Smaller codebase, easier to debug
- **Developer Experience**: Better onboarding, easier contributions

### Rollback Plan

**If migration fails**:

1. Revert `openproject-mcp.py` to import old server
2. Keep `openproject-mcp.legacy.py` as backup
3. All configs continue to work (no user impact)
4. Analyze failure, fix issues, retry

---

## 9. Success Metrics

### Code Quality Metrics

- [ ] **Lines of Code**: Reduce from 3,213 to ~1,500 (53% reduction)
- [ ] **Cyclomatic Complexity**: Eliminate 1,222-line elif block
- [ ] **Test Coverage**: Achieve >80% coverage
- [ ] **Type Hints**: 100% of tool functions typed

### Performance Metrics

- [ ] **Response Time**: No regression (within 5%)
- [ ] **Memory Usage**: No significant increase
- [ ] **Startup Time**: No significant increase

### Developer Experience Metrics

- [ ] **Time to Add Tool**: <30 minutes (vs 60+ minutes currently)
- [ ] **Onboarding Time**: <2 hours for new contributor
- [ ] **Bug Fix Time**: 50% reduction (easier to debug)

### Functional Metrics

- [ ] **All 40 Tools Working**: 100% functionality preserved
- [ ] **Test Pass Rate**: >95% on all tests
- [ ] **Integration Tests**: All critical workflows passing
- [ ] **Claude Desktop**: Zero user-facing changes

---

## 10. Timeline Estimate

**Total**: 20-30 development hours + 10 hours buffer = **30-40 hours**

| Phase                         | Duration        | Deliverable                    |
| ----------------------------- | --------------- | ------------------------------ |
| Phase 0: Preparation          | 1-2 hours       | Directory structure, utilities |
| Phase 1: POC                  | 2-4 hours       | 2 tools migrated, tested       |
| Phase 2: Core Tools           | 6-8 hours       | 19 tools migrated, tested      |
| Phase 3: Advanced Tools       | 6-8 hours       | 21 tools migrated, tested      |
| Phase 4: Testing & Refinement | 4-6 hours       | Full test suite, docs          |
| Phase 5: Cutover              | 1 hour          | Production ready               |
| **Subtotal**                  | **20-30 hours** |                                |
| Buffer (bugs, issues)         | 10 hours        |                                |
| **Total**                     | **30-40 hours** | Complete migration             |

**Calendar Time**: 1-2 weeks (depends on team availability)

---

## 11. Recommendations & Next Steps

### Immediate Actions

1. **Review This Plan**: Team review, gather feedback
2. **Approve Architecture**: Confirm modular structure is acceptable
3. **Set Timeline**: Allocate developer time
4. **Prepare Environment**: Install FastMCP, create branches

### Long-Term Considerations

1. **Resources**: Consider adding MCP resources for:

   - Project schemas
   - Work package templates
   - Recent activity feed

2. **Prompts**: Consider adding MCP prompts for:

   - Project analysis workflows
   - Work package generation templates
   - Status report generation

3. **HTTP Transport**: Enable web-based access for:

   - Web applications
   - API integrations
   - Remote Claude instances

4. **Authentication**: Add OAuth/JWT if exposing publicly

5. **Monitoring**: Add structured logging, metrics

### Decision Points

**Option A: Full Migration (Recommended)**

- Pros: Clean codebase, best long-term maintainability
- Cons: 30-40 hours investment
- When: When team has dedicated time

**Option B: Hybrid Approach**

- Pros: Lower risk, gradual transition
- Cons: Two codebases to maintain temporarily
- When: Limited developer time, need incremental progress

**Option C: Defer Migration**

- Pros: No immediate work
- Cons: Technical debt accumulates, harder to maintain
- When: No resources available, higher priorities

**Recommendation**: **Option A (Full Migration)** - The benefits far outweigh the costs, and the codebase is at an ideal size for migration (not too large, not too small).

---

## 12. Key Takeaways

1. **FastMCP Dramatically Simplifies MCP Servers**: ~60% code reduction is achievable
2. **Decorator Pattern > Manual Schemas**: Less boilerplate, more productivity
3. **In-Memory Testing**: Game-changer for unit tests
4. **Type Safety**: Automatic schema generation reduces errors
5. **Modular Structure**: Easier to maintain and extend
6. **Backward Compatible**: No user impact, same Claude Desktop config
7. **Manageable Effort**: 30-40 hours for complete migration
8. **High ROI**: Pays for itself in reduced maintenance time

---

## Appendix A: Tool-by-Tool Migration Map

| #         | Tool Name                    | Current Lines | New Lines | File             | Complexity | Priority |
| --------- | ---------------------------- | ------------- | --------- | ---------------- | ---------- | -------- |
| 1         | test_connection              | 45            | 20        | connection.py    | Low        | P0 (POC) |
| 2         | check_permissions            | 50            | 25        | connection.py    | Low        | P2       |
| 3         | list_projects                | 60            | 30        | projects.py      | Low        | P0 (POC) |
| 4         | get_project                  | 40            | 20        | projects.py      | Low        | P2       |
| 5         | create_project               | 80            | 40        | projects.py      | Medium     | P2       |
| 6         | update_project               | 90            | 45        | projects.py      | Medium     | P2       |
| 7         | delete_project               | 40            | 20        | projects.py      | Low        | P2       |
| 8         | list_work_packages           | 120           | 60        | work_packages.py | Medium     | P2       |
| 9         | get_work_package             | 60            | 30        | work_packages.py | Low        | P2       |
| 10        | create_work_package          | 150           | 75        | work_packages.py | High       | P2       |
| 11        | update_work_package          | 160           | 80        | work_packages.py | High       | P3       |
| 12        | delete_work_package          | 40            | 20        | work_packages.py | Low        | P3       |
| 13        | list_types                   | 50            | 25        | work_packages.py | Low        | P2       |
| 14        | list_statuses                | 50            | 25        | work_packages.py | Low        | P2       |
| 15        | list_priorities              | 50            | 25        | work_packages.py | Low        | P2       |
| 16        | set_work_package_parent      | 60            | 30        | hierarchy.py     | Medium     | P3       |
| 17        | remove_work_package_parent   | 50            | 25        | hierarchy.py     | Low        | P3       |
| 18        | list_work_package_children   | 80            | 40        | hierarchy.py     | Medium     | P3       |
| 19        | create_work_package_relation | 100           | 50        | relations.py     | Medium     | P3       |
| 20        | list_work_package_relations  | 90            | 45        | relations.py     | Medium     | P3       |
| 21        | get_work_package_relation    | 70            | 35        | relations.py     | Low        | P3       |
| 22        | update_work_package_relation | 80            | 40        | relations.py     | Medium     | P3       |
| 23        | delete_work_package_relation | 40            | 20        | relations.py     | Low        | P3       |
| 24        | list_users                   | 60            | 30        | users.py         | Low        | P2       |
| 25        | get_user                     | 50            | 25        | users.py         | Low        | P2       |
| 26        | list_roles                   | 50            | 25        | users.py         | Low        | P2       |
| 27        | get_role                     | 60            | 30        | users.py         | Low        | P2       |
| 28        | list_memberships             | 80            | 40        | memberships.py   | Medium     | P3       |
| 29        | get_membership               | 50            | 25        | memberships.py   | Low        | P3       |
| 30        | create_membership            | 90            | 45        | memberships.py   | Medium     | P3       |
| 31        | update_membership            | 80            | 40        | memberships.py   | Medium     | P3       |
| 32        | delete_membership            | 40            | 20        | memberships.py   | Low        | P3       |
| 33        | list_project_members         | 70            | 35        | memberships.py   | Low        | P3       |
| 34        | list_user_projects           | 70            | 35        | memberships.py   | Low        | P3       |
| 35        | list_time_entries            | 80            | 40        | time_entries.py  | Medium     | P3       |
| 36        | create_time_entry            | 90            | 45        | time_entries.py  | Medium     | P3       |
| 37        | update_time_entry            | 80            | 40        | time_entries.py  | Medium     | P3       |
| 38        | delete_time_entry            | 40            | 20        | time_entries.py  | Low        | P3       |
| 39        | list_time_entry_activities   | 50            | 25        | time_entries.py  | Low        | P3       |
| 40        | list_versions                | 60            | 30        | versions.py      | Low        | P3       |
| 41        | create_version               | 90            | 45        | versions.py      | Medium     | P3       |
| **Total** | **3,213**                    | **1,485**     |           |                  |            |

**Priority Legend**:

- **P0**: Proof of Concept (Phase 1)
- **P2**: Core Tools (Phase 2)
- **P3**: Advanced Features (Phase 3)

**Code Reduction**: 3,213 → 1,485 lines = **53.8% reduction**

---

## Appendix B: FastMCP Resources

**Official Documentation**:

- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [FastMCP Website](https://www.prefect.io/fastmcp)
- [MCP Guides](https://mcpcat.io/guides/building-mcp-server-python-fastmcp/)
- [DataCamp Tutorial](https://www.datacamp.com/tutorial/building-mcp-server-client-fastmcp)

**Examples**:

- [Firecrawl Tutorial](https://www.firecrawl.dev/blog/fastmcp-tutorial-building-mcp-servers-python)
- [GoFastMCP Tutorial](https://gofastmcp.com/tutorials/create-mcp-server)
- [Pondhouse Guide](https://www.pondhouse-data.com/blog/create-mcp-server-with-fastmcp)

**PyPI**:

- [fastmcp on PyPI](https://pypi.org/project/fastmcp/)

**Community**:

- MCP Discord
- FastMCP GitHub Issues

---

**END OF MIGRATION PLAN**

This plan is a living document. Update as migration progresses and new insights emerge.
PLAN_EOF
