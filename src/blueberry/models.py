from pydantic import BaseModel, Field, RootModel
from typing import Dict, Optional, List, Any, Union


class Intent(BaseModel):
    name: str = Field(description="The name of the intent")
    description: str = Field(description="The description of the intent")
    features: list[str] = Field(
        description="The features of the intent", default_factory=list
    )
    preferences: Optional[Dict[str, str | List[str]]] = Field(
        description="User preferences for the project", default=None
    )


class ApiEndpoint(BaseModel):
    path: str = Field(description="The endpoint path")
    method: str = Field(description="The HTTP method")
    description: str = Field(description="Description of what the endpoint does")
    auth_required: bool = Field(description="Whether authentication is required", default=False)
    parameters: Optional[List[Dict[str, str]]] = Field(description="List of parameters", default=None)
    possible_responses: Optional[List[Dict[str, str]]] = Field(description="List of possible responses", default=None)


class DataModel(BaseModel):
    name: str = Field(description="The name of the model")
    fields: Dict[str, str] = Field(description="The fields and their types")
    relationships: Optional[List[str]] = Field(description="List of relationships", default=None)


class AuthConfig(BaseModel):
    providers: List[str] = Field(description="List of auth providers")
    roles: Optional[List[str]] = Field(description="List of roles", default=None)
    custom_claims: Optional[Dict[str, str]] = Field(description="Custom claims", default=None)


class DatabaseConfig(BaseModel):
    type: str = Field(description="The type of database")
    auth_config: AuthConfig = Field(description="Authentication configuration")


class DeploymentConfig(BaseModel):
    platform: str = Field(description="The deployment platform")
    region: Optional[str] = Field(description="The deployment region", default=None)
    environment_variables: Optional[Dict[str, str]] = Field(description="Environment variables", default=None)
    build_settings: Optional[Dict[str, str]] = Field(description="Build settings", default=None)


class TechStack(BaseModel):
    name: str = Field(description="The name of the project")
    description: str = Field(description="Detailed description of the project")
    techStack: List[str] = Field(description="List of technologies used in the project")


class PageComponent(BaseModel):
    type: str = Field(description="The type of page (SSR, Static, SSG)")
    components: List[str] = Field(description="List of components used in the page")
    authRequired: Optional[bool] = Field(description="Whether authentication is required", default=None)
    authRedirect: Optional[str] = Field(description="Redirect path for authenticated users", default=None)
    dataFetching: Optional[List[str]] = Field(description="List of data to be fetched", default=None)


class FrontendStructure(BaseModel):
    pages: Dict[str, PageComponent] = Field(description="Pages configuration")
    components: Dict[str, List[str]] = Field(description="Shared components configuration")


class ApiMethod(BaseModel):
    method: Optional[str] = Field(description="HTTP method", default=None)
    middleware: Optional[List[str]] = Field(description="List of middleware", default=None)
    validation: Optional[List[str]] = Field(description="List of validation fields", default=None)
    supabase: str = Field(description="Supabase query")
    body: Optional[Dict[str, str]] = Field(description="Request body schema", default=None)
    response: Optional[Dict[str, str]] = Field(description="Response schema", default=None)
    pagination: Optional[bool] = Field(description="Whether pagination is enabled", default=None)


class ApiRouteGroup(RootModel):
    root: Dict[str, Union[ApiMethod, Dict[str, ApiMethod]]]


class TableConfig(BaseModel):
    columns: Dict[str, str] = Field(description="Table columns and their types")
    RLS: Optional[Dict[str, str]] = Field(description="Row Level Security policies", default=None)


class SupabaseConfig(BaseModel):
    tables: Dict[str, TableConfig] = Field(description="Database tables configuration")
    indexes: List[str] = Field(description="Database indexes")


class ProjectSpec(BaseModel):
    project: TechStack = Field(description="Project overview and tech stack")
    frontendStructure: FrontendStructure = Field(description="Frontend structure configuration")
    apiRoutes: Dict[str, ApiRouteGroup] = Field(description="API routes configuration")
    supabaseConfig: SupabaseConfig = Field(description="Supabase configuration")
    features: Dict[str, List[str]] = Field(description="Feature categories and their items")
    dependencies: Dict[str, List[str]] = Field(description="Project dependencies")
    environmentVariables: Dict[str, str] = Field(description="Required environment variables")
    acceptanceCriteria: List[str] = Field(description="Acceptance criteria for the project")



    pass
