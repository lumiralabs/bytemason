from pydantic import BaseModel, Field


class Intent(BaseModel):
    name: str = Field(description="The name of the intent")
    description: str = Field(description="The description of the intent")


class BaseSpec(BaseModel):
    name: str = Field(description="The name of the spec")
    description: str = Field(description="The description of the spec")


class OpenAPISpec(BaseSpec):
    pass


class FrontendSpec(BaseSpec):
    pass


class BackendServingSpec(BaseSpec):
    pass


class SupabaseSpec(BaseSpec):
    pass


class SupabaseAuthSpec(BaseSpec):
    pass
