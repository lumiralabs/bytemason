from typing import Dict, List
from pydantic import BaseModel

class Intent(BaseModel):
    features: List[str]

class ProjectSpec(BaseModel):
    id: str
    object: str
    created: int
    name: str
    description: str
    tech_stack: List[str]
    components: List[str]
    api_routes: List[str]
    database_tables: List[str]
    env_vars: Dict[str, str]
    usage: Dict[str, int]
    system_fingerprint: str