from pydantic import BaseModel, Field


class Intent(BaseModel):
    name: str = Field(description="The name of the intent")
    description: str = Field(description="The description of the intent")
    features: list[str] = Field(
        description="The features of the intent", default_factory=list
    )
    pages: list[str] = Field(
        description="The pages of the intent", default_factory=list
    )


class BaseSpec(BaseModel):
    name: str = Field(description="The name of the spec")
    description: str = Field(description="The description of the spec")


class OpenAPISpec(BaseSpec):
    openapi_spec: str = Field(description="The OpenAPI spec for the API")
    pass


class FrontendSpec(BaseSpec):
    pass


class BackendServingSpec(BaseSpec):
    pass


class SupabaseSpec(BaseSpec):
    pass


class SupabaseAuthSpec(BaseSpec):
    pass
