from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from enum import Enum


class Intent(BaseModel):
    app_name: str = Field(..., description="Concise name for the application")
    primary_purpose: str = Field(..., description="Single-sentence description of the app's core purpose")
    user_types: list[str] = Field(..., description="Different user roles in the system")
    core_features: list[str] = Field(..., description="Essential features with priority and complexity")
    data_entities: list[str] = Field(..., description="Key data models with their critical attributes")
    auth_requirements: List[str] = Field(..., description="Authentication and authorization needs")
    integration_requirements: list[str] = Field(..., description="External systems that must be integrated")
    constraints: list[str] = Field(..., description="Technical or business limitations to consider")



class SupabaseTable(BaseModel):
    name: str = Field(..., description="Name of the table")
    sql_schema: str = Field(
        ...,
        description="SQL schema for creating the table including types and relationships",
    )


class APIRoute(BaseModel):
    path: str = Field(..., description="API route path (e.g., /api/users)")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE)")
    description: str = Field(..., description="What this API route does and returns")
    query: str = Field(..., description="Supabase query or SQL to be used")


class Page(BaseModel):
    path: str = Field(..., description="Route path (e.g., /dashboard)")
    description: str = Field(..., description="What this page does")
    api_routes: list[str] = Field(..., description="API routes this page uses")
    components: list[str] = Field(..., description="UI components used on this page")


class Component(BaseModel):
    name: str = Field(..., description="Name of the component")
    description: str = Field(..., description="What this component does")
    is_client: bool = Field(..., description="Whether this is a client component")


class ProjectStructure(BaseModel):
    pages: list[Page] = Field(..., description="App pages/routes")
    components: list[Component] = Field(..., description="Reusable UI components")
    api_routes: list[APIRoute] = Field(..., description="API endpoints")
    database: list[SupabaseTable] = Field(..., description="Database tables")


class ProjectSpec(BaseModel):
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project purpose")
    features: list[str] = Field(..., description="Features to implement")
    structure: ProjectStructure = Field(..., description="Project structure")


class FileMode(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class FileContent(BaseModel):
    path: str = Field(..., description="Relative path from project root")
    content: str = Field(..., description="Complete file content")
    mode: FileMode = Field(default=FileMode.CREATE, description="File operation mode")
    modify_strategy: Optional[str] = Field(
        None, description="Strategy for file modifications"
    )


class GeneratedCode(BaseModel):
    files: list[FileContent] = Field(..., description="List of files to create/modify")
    dependencies: list[str] = Field(
        default_factory=list, description="Additional npm dependencies needed"
    )
    errors: list[str] = Field(
        default_factory=list, description="Any generation warnings or errors"
    )


class BuildError(BaseModel):
    file: str = Field(..., description="File path where error occurred")
    line: int = Field(..., description="Line number of error")
    column: int = Field(..., description="Column number of error")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type (e.g., 'TypeError', 'SyntaxError')")
    code: str = Field(..., description="Error code if available")


class BuildErrorReport(BaseModel):
    errors: list[BuildError] = Field(..., description='List of build errors extracted from logs')

class ErrorAnalysis(BaseModel):
    """AI analysis of a build error"""
    cause: str = Field(..., description="Root cause of the error")
    suggested_fix: str = Field(..., description="Suggested approach to fix the error") 
    required_imports: list[str] = Field([], description="Any imports that need to be added")
    dependencies: list[str] = Field([], description="Any npm dependencies that need to be installed")


class AgentAction(BaseModel):
    """Action to be taken by the repair agent"""
    tool: str = Field(..., description="Name of the tool to use")
    input: str = Field(..., description="Input for the tool as a string")
    thought: str = Field(..., description="Reasoning behind this action")


class AgentResponse(BaseModel):
    """Response from the repair agent's AI"""
    thought: str = Field(..., description="Current thinking about the problem")
    action: Optional[AgentAction] = Field(..., description="Next action to take, if any")
    status: str = Field(..., description="Current status: 'thinking', 'fixed', 'failed'")
    explanation: Optional[str] = Field(..., description="Explanation of the status if fixed/failed")


class FileOperation(BaseModel):
    """Result of a file operation"""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Description of what happened")
    path: Optional[str] = Field(..., description="Path to the file that was operated on")
    content: Optional[str] = Field(..., description="File content if relevant")


class DirectoryListing(BaseModel):
    path: str = Field(..., description="Directory path relative to project root")
    exists: bool = Field(..., description="Whether the directory exists")
    is_empty: bool = Field(..., description="Whether the directory is empty")
    files: List[str] = Field(..., description="List of file paths")
    directories: List[str] = Field(..., description="List of directory paths")
    error: str = Field("", description="Error message if something went wrong")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "is_empty": self.is_empty,
            "files": self.files,
            "directories": self.directories,
            "error": self.error
        }
