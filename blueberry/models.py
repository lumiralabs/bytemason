from pydantic import BaseModel, Field

class Intent(BaseModel):
    name: str = Field(description="The name of the intent")
    description: str = Field(description="The description of the intent")
