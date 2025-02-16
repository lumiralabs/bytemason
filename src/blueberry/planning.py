from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json

class FileSpec(BaseModel):
    """Specification for a file to be generated"""
    path: str
    content: str
    description: str = ""

class ComponentSpec(BaseModel):
    """Specification for a React component"""
    name: str
    path: str
    code: str
    test_code: Optional[str] = None

class ApiRouteSpec(BaseModel):
    """Specification for an API route"""
    path: str
    code: str
    test_code: Optional[str] = None

class DatabaseSpec(BaseModel):
    """Database implementation specification"""
    migrations: List[Dict[str, str]]
    initialization_code: str

class AuthSpec(BaseModel):
    """Authentication implementation specification"""
    middleware: str
    components: List[Dict[str, str]]
    utils: Dict[str, str]

class ProjectPlan(BaseModel):
    """Project implementation plan"""
    files: List[FileSpec]
    components: List[ComponentSpec]
    api_routes: List[ApiRouteSpec]
    database: DatabaseSpec
    auth: AuthSpec

def create_project_plan(spec: dict, scaffold: dict, client) -> ProjectPlan:
    """
    Create a detailed project implementation plan using LLM, based on scaffold and spec.
    """
    system_prompt = """You are an expert full-stack developer. Create a complete implementation plan for a Next.js + Supabase application.
    Use the provided scaffold as the base structure and enhance it with the specification requirements.

    The scaffold provides:
    1. Base file structure and patterns
    2. Component templates and features
    3. API route patterns
    4. Authentication setup
    5. Configuration files

    Follow these steps:
    1. Start with the scaffold's structure
    2. Add/modify files based on the spec's requirements
    3. Use scaffold's patterns for consistency
    4. Implement spec's features and requirements
    5. Follow scaffold's configuration patterns

    For each file:
    1. Check if it exists in scaffold
    2. If yes, use scaffold's structure and enhance it
    3. If no, create new following scaffold's patterns
    4. Add spec's requirements and features

    The response should be a JSON object with this structure:
    {
        "files": [
            {
                "path": "relative/path/to/file",
                "content": "complete file content with scaffold patterns",
                "description": "what the file does"
            }
        ],
        "components": [
            {
                "name": "ComponentName",
                "path": "path/to/component",
                "code": "component code following scaffold patterns",
                "test_code": "optional test code"
            }
        ],
        "api_routes": [
            {
                "path": "api/route/path",
                "code": "route handler following scaffold patterns",
                "test_code": "optional test code"
            }
        ],
        "database": {
            "migrations": [
                {
                    "name": "migration name",
                    "sql": "SQL migration code"
                }
            ],
            "initialization_code": "database initialization code"
        },
        "auth": {
            "middleware": "middleware code from scaffold + spec requirements",
            "components": [
                {
                    "name": "component name",
                    "code": "auth component code"
                }
            ],
            "utils": {
                "filename": "utility code"
            }
        }
    }

    Important:
    1. Use scaffold's structure as the foundation
    2. Follow scaffold's patterns and conventions
    3. Implement spec's features and requirements
    4. Maintain consistency with scaffold's styling
    5. Use scaffold's dependencies and versions
    6. Follow scaffold's TypeScript patterns
    7. Use scaffold's authentication patterns
    8. Maintain scaffold's file organization"""

    try:
        # First, analyze scaffold and spec
        analysis_prompt = f"""Analyze the scaffold and spec to create a merged implementation plan:

        Scaffold Structure:
        {json.dumps(scaffold.get('structure', {}), indent=2)}

        Scaffold Features:
        {json.dumps(scaffold.get('features', []), indent=2)}

        Project Spec:
        {json.dumps(spec, indent=2)}

        Create a plan that:
        1. Uses scaffold's structure as base
        2. Implements spec's features
        3. Follows scaffold's patterns
        4. Maintains consistency
        """

        # Get implementation plan
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            response_format={"type": "json_object"}
        )

        plan_dict = json.loads(completion.choices[0].message.content)
        
        # Validate plan against scaffold and spec
        validate_prompt = f"""Validate the implementation plan:

        Plan:
        {json.dumps(plan_dict, indent=2)}

        Verify:
        1. All scaffold base files are included
        2. All spec features are implemented
        3. Patterns are consistent
        4. Dependencies are correct
        5. File structure matches scaffold

        Return the validated and corrected plan.
        """

        # Validate and finalize plan
        validation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a code review expert. Validate and correct the implementation plan."
                },
                {
                    "role": "user",
                    "content": validate_prompt
                }
            ],
            response_format={"type": "json_object"}
        )

        validated_plan = json.loads(validation.choices[0].message.content)
        return ProjectPlan(**validated_plan)

    except Exception as e:
        raise Exception(f"Error creating project plan: {str(e)}")

def generate_file_content(path: str, description: str, scaffold: dict, client) -> str:
    """
    Generate complete implementation code for a file, using scaffold as reference.
    """
    # Find matching scaffold file pattern
    scaffold_pattern = None
    for file_path, file_info in scaffold.get('structure', {}).get('root', {}).items():
        if path.endswith(file_path) or path.startswith(file_path):
            scaffold_pattern = file_info
            break

    system_prompt = f"""You are an expert Next.js developer. Generate ONLY the code implementation for:
    Path: {path}
    Description: {description}

    Important:
    1. Output ONLY the code implementation
    2. NO explanations or comments outside the code
    3. NO markdown formatting
    4. NO conversation or additional text
    5. Start directly with the code (imports, etc.)
    6. Follow the scaffold pattern exactly
    7. Include only necessary JSDoc comments within the code
    8. Use TypeScript types and interfaces
    9. Follow the exact file structure from scaffold

    Scaffold Pattern:
    {json.dumps(scaffold_pattern, indent=2) if scaffold_pattern else "No direct pattern found"}

    Dependencies: {json.dumps(scaffold.get('dependencies', {}), indent=2)}"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": "Generate ONLY the code implementation, no additional text or explanations."
                }
            ]
        )

        code = completion.choices[0].message.content
        
        # Clean up any potential markdown or extra text
        if code.startswith("```"):
            code = code[code.find("\n")+1:]
            if code.endswith("```"):
                code = code[:-3]
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        return code

    except Exception as e:
        raise Exception(f"Error generating code for {path}: {str(e)}") 