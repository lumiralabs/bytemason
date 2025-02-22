from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Intent(BaseModel):
    features: list[str] = Field(
        ..., description="Core features extracted from user's request"
    )


class SupabaseTable(BaseModel):
    name: str = Field(..., description="Name of the table")
    schema_: str = Field(
        ...,
        description="SQL schema for creating the table including types and relationships",
        alias="schema",
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
    line: Optional[int] = Field(None, description="Line number of error")
    column: Optional[int] = Field(None, description="Column number of error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code if available")
    type: str = Field(..., description="Error type (e.g., 'TypeError', 'SyntaxError')")
