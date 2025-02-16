from lumos import lumos
from blueberry.models import Intent, ProjectSpec, ApiMethod
from blueberry.planning import ProjectPlan, create_project_plan, generate_file_content
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
import json
import os
from openai import OpenAI
from pathlib import Path
from typing import Dict, List, Union, Any
import shutil
from pydantic import BaseModel


class MasterAgent:
    def __init__(self):
        pass

    def understand_intent(self, user_input: str) -> Intent:
        """
        Understand the user's intent from the user's input, and returns a more detailed intent with features, components, etc.
        """
        system_prompt = """Analyze user requests for Next.js + Supabase applications and break them down into core features.

        Focus on:
        1. Core functionality and key features
        2. Required auth/security features
        3. Essential data models
        4. Critical API endpoints

        Format features as specific, actionable items like:
        - "Email and social authentication"
        - "Real-time chat messaging"
        - "File upload with image optimization"

        Consider security, performance, and user experience in your analysis."""
        
        intent = lumos.call_ai(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": user_input},
            ],
            response_format=Intent,
            model="gpt-4o-mini",
        )
        
        # Ensure we have a name and description
        if not intent.name:
            intent.name = user_input.strip().lower().replace(" ", "-")
        if not intent.description:
            intent.description = f"A Next.js application that {user_input}"
            
        return intent

    def validate_feature(self, feature: str) -> str:
        """Validate and enhance a single feature.
        
        Args:
            feature: The feature to validate and enhance
            
        Returns:
            str: The validated/enhanced feature description
        """
        system_prompt = """You are an expert in writing clear, specific feature descriptions for web applications.
Given a feature description, enhance it to be more specific and actionable.

Guidelines:
- Make it clear and specific
- Include key functionality aspects
- Consider security and UX implications
- Keep it concise but complete

Example Input: "User authentication"
Example Output: "Email and social authentication with JWT tokens and password reset"
"""
        
        intent = lumos.call_ai(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": f"Enhance this feature: {feature}"}
            ],
            response_format=Intent,
            model="gpt-4o-mini",
        )
        
        return intent.features[0] if intent.features else feature

    def verify_with_user_loop(self, intent: Intent, max_attempts=3) -> Intent:
        """Verify the intent with the user, iterate with feedback and returns the final intent.
        
        Args:
            intent: The initial intent to verify
            max_attempts: Maximum number of modification attempts
            
        Returns:
            Intent: The verified and potentially modified intent
        """
        
        console = Console()
        
        attempts = 0
        while attempts < max_attempts:
            # Display current features
            console.print("\n[bold yellow]Current features:[/bold yellow]")
            for i, feature in enumerate(intent.features, 1):
                console.print(f"{i}. {feature}")
            
            if not Confirm.ask("\nWould you like to modify these features?"):
                break
                
            # Show modification options
            console.print("\n[bold]Options:[/bold]")
            console.print("1. Add a feature")
            console.print("2. Remove a feature")
            console.print("3. Done modifying")
            
            choice = Prompt.ask("What would you like to do?", choices=["1", "2", "3"])
            
            if choice == "1":
                new_feature = Prompt.ask("Enter new feature")
                
                # Validate and enhance the feature with AI
                if Confirm.ask("Would you like AI to validate and enhance this feature?"):
                    status = console.status("[bold green]Validating feature...")
                    status.start()
                    try:
                        enhanced_feature = self.validate_feature(new_feature)
                        if enhanced_feature != new_feature:
                            status.stop()
                            if Confirm.ask(f"Would you like to use the enhanced version: {enhanced_feature}?"):
                                new_feature = enhanced_feature
                        else:
                            status.stop()
                    except Exception as e:
                        status.stop()
                        console.print(f"[red]Error validating feature: {e}[/red]")
                
                intent.features.append(new_feature)
                
            elif choice == "2":
                if not intent.features:
                    console.print("[yellow]No features to remove[/yellow]")
                    continue
                    
                remove_idx = int(Prompt.ask(
                    "Enter number of feature to remove",
                    choices=[str(i) for i in range(1, len(intent.features) + 1)]
                )) - 1
                intent.features.pop(remove_idx)
                
            else:  # choice == "3"
                break
            
            attempts += 1
            
            # Show updated features
            console.print("\n[bold yellow]Updated features:[/bold yellow]")
            for i, feature in enumerate(intent.features, 1):
                console.print(f"{i}. {feature}")
        
        return intent

    def create_spec(self, intent: Intent) -> ProjectSpec:
        """Create a detailed project specification based on the intent and preferences.
        
        Args:
            intent: The intent object containing project requirements and preferences.
            
        Returns:
            ProjectSpec: A detailed project specification ready for implementation.
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        client = OpenAI()
        console = Console()
        
        console.log('🚀 [Spec Generation] Processing intent:', intent.model_dump_json())
        
        try:
            console.log('📡 [Spec Generation] Making OpenAI API call...')
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert full-stack developer specializing in Next.js and Supabase applications. Generate a detailed specification for a web application based on the user's prompt.
                        
                        The specification should follow this exact structure:
                        {
                          "project": {
                            "name": "string - use the intent name",
                            "description": "string - use the intent description",
                            "techStack": ["Next.js 14", "Supabase", "TypeScript", "Tailwind CSS", ...]
                          },
                          "frontendStructure": {
                            "pages": {
                              "/path": {
                                "type": "SSR|Static|SSG",
                                "components": ["array of components"],
                                "authRequired": boolean,
                                "dataFetching": ["data to fetch"]
                              }
                            },
                            "components": {
                              "shared": ["reusable components"],
                              "feature": ["feature-specific components"]
                            }
                          },
                          "apiRoutes": {
                            "group": {
                              "/api/path": {
                                "method": "HTTP method",
                                "middleware": ["auth checks"],
                                "supabase": "supabase query",
                                "validation": ["required fields"]
                              }
                            }
                          },
                          "supabaseConfig": {
                            "tables": {
                              "tableName": {
                                "columns": {"column": "type"},
                                "RLS": {"policy": "condition"}
                              }
                            },
                            "indexes": ["SQL index statements"]
                          },
                          "features": {
                            "category": ["feature list - use intent features"]
                          },
                          "dependencies": {
                            "required": ["prod dependencies"],
                            "dev": ["dev dependencies"]
                          },
                          "environmentVariables": {
                            "VAR_NAME": "type"
                          },
                          "acceptanceCriteria": [
                            "list of criteria"
                          ]
                        }

                        Important:
                        1. Use the intent.name for project.name
                        2. Use the intent.description for project.description
                        3. Use the intent.features to populate the features section
                        4. If intent.preferences exist, use them to customize the specification
                        
                        Guidelines:
                        1. Always include authentication and authorization
                        2. Use TypeScript and modern React patterns
                        3. Implement proper security measures
                        4. Consider performance optimizations
                        5. Follow Next.js best practices for routing and data fetching
                        6. Include proper error handling
                        7. Add comprehensive validation
                        8. Consider real-time features where appropriate"""
                    },
                    {
                        "role": "user",
                        "content": f"Generate a JSON specification for the following app: {json.dumps(intent.model_dump(), indent=2)}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            console.log('✅ [Spec Generation] OpenAI API call successful')

            message = completion.choices[0].message
            if not message.content:
                console.log('❌ [Spec Generation] No valid response from OpenAI')
                raise ValueError("Failed to generate specification: Empty response from OpenAI")

            try:
                spec_dict = json.loads(message.content)
                console.log('✨ [Spec Generation] Parsed JSON response')
                
                # Ensure project name and description are set from intent
                if "project" not in spec_dict:
                    spec_dict["project"] = {}
                spec_dict["project"]["name"] = intent.name
                spec_dict["project"]["description"] = intent.description
                
                spec = ProjectSpec.model_validate(spec_dict)
                console.log('🎉 [Spec Generation] Validated specification schema')
                return spec
                
            except json.JSONDecodeError as e:
                console.log('💥 [Spec Generation] Failed to parse JSON response')
                raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")
            except Exception as e:
                console.log('💥 [Spec Generation] Failed to validate specification')
                raise ValueError(f"Invalid specification format: {str(e)}")
            
        except Exception as e:
            console.log('💥 [Spec Generation] Error:', str(e))
            raise


class TestAgent:
    def __init__(self, spec):
        self.spec = spec

    def backend_serving_test(self):
        """
        Hits each endpoint in the backend serving spec, and verifies everything works as expected
        """

        # create a test client
        # hit each endpoint
        # verify the response
        # return the results
        client = httpx.Client()
        for endpoint in self.spec.endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            assert response.json() == {"message": "Hello, World!"}
        pass


# class Sandbox(BaseModel):
#     filesystem: Any
#     terminal: Any
#     code_editor: Any


#     def execute(self, code_input: str):
#         """
#         Executes the code commands in the terminal and returns the output
#         """
#         pass


class RepairAgent:
    def __init__(self, spec):
        self.spec = spec

    def repair(self, terminal_output: str, code_input: str):
        """
        Repairs the code based on the outputs of the terminal results
        """
        pass


class ProjectPlan(BaseModel):
    """Project generation plan created by LLM"""
    file_structure: Dict[str, Any]
    components: List[Dict[str, Any]]
    api_routes: List[Dict[str, Any]]
    database: Dict[str, Any]
    auth: Dict[str, Any]
    config_files: List[Dict[str, Any]]


class CodeGeneratorAgent:
    def __init__(self, spec: ProjectSpec, scaffold_config: dict):
        self.spec = spec
        self.scaffold = scaffold_config
        self.console = Console()
        self.client = OpenAI()

    def ensure_directory(self, path: Path) -> None:
        """Ensures a directory exists, creating it and all parent directories if necessary."""
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.console.print(f"[red]Error creating directory {path}: {str(e)}[/red]")
            raise

    def write_file(self, path: Path, content: str) -> None:
        """Safely writes content to a file, ensuring the parent directory exists."""
        try:
            self.ensure_directory(path.parent)
            path.write_text(content)
        except Exception as e:
            self.console.print(f"[red]Error writing file {path}: {str(e)}[/red]")
            raise

    def clean_path(self, path_str: str) -> str:
        """Cleans and normalizes a path string."""
        return path_str.strip("/").replace("//", "/")

    def clean_code(self, code: str) -> str:
        """Clean up generated code to remove any extra text or formatting."""
        if not code:
            return ""
            
        # Remove markdown code blocks
        if code.startswith("```"):
            code = code[code.find("\n")+1:]
            if code.endswith("```"):
                code = code[:-3]
        
        # Remove any potential language specifier
        first_line = code.split("\n")[0]
        if first_line.startswith("typescript") or first_line.startswith("javascript"):
            code = "\n".join(code.split("\n")[1:])
        
        # Remove any leading/trailing whitespace
        code = code.strip()
        
        return code

    def write_code_file(self, path: Path, code: str) -> None:
        """Write code to a file after cleaning it."""
        clean_code = self.clean_code(code)
        if not clean_code:
            raise ValueError(f"No valid code content for {path}")
        self.write_file(path, clean_code)

    def generate(self, output_dir: str):
        """Generate the full-stack codebase using scaffold as base."""
        output_path = None
        try:
            output_path = Path(output_dir)
            self.ensure_directory(output_path)
            
            # Validate scaffold configuration
            if not self.scaffold or not isinstance(self.scaffold, dict):
                raise ValueError("Invalid scaffold configuration")
            if "structure" not in self.scaffold or "root" not in self.scaffold["structure"]:
                raise ValueError("Invalid scaffold structure")
            
            # Step 1: Create implementation plan based on scaffold
            self.console.print("[bold blue]1. Creating implementation plan...[/bold blue]")
            plan = create_project_plan(
                spec=self.spec.model_dump(),
                scaffold=self.scaffold,
                client=self.client
            )
            
            # Validate plan
            if not plan.files or not plan.components or not plan.api_routes:
                raise ValueError("Implementation plan is incomplete")
            
            # Step 2: Create base directories from scaffold
            self.console.print("[bold blue]2. Creating directory structure...[/bold blue]")
            scaffold_dirs = []
            for path, info in self.scaffold["structure"]["root"].items():
                if isinstance(info, dict) and info.get("type") == "directory":
                    scaffold_dirs.append(path)
            
            if not scaffold_dirs:
                raise ValueError("No directories found in scaffold")
            
            for directory in scaffold_dirs:
                self.ensure_directory(output_path / directory)
            
            # Step 3: Write all files following scaffold patterns
            self.console.print("[bold blue]3. Writing project files...[/bold blue]")
            generated_files = []
            for file in plan.files:
                try:
                    file_path = output_path / self.clean_path(file.path)
                    # Generate content using scaffold as reference
                    content = generate_file_content(
                        path=file.path,
                        description=file.description,
                        scaffold=self.scaffold,
                        client=self.client
                    )
                    self.write_code_file(file_path, content)
                    generated_files.append(file_path)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate {file.path}: {str(e)}[/yellow]")
                    continue
            
            # Step 4: Write components following scaffold patterns
            self.console.print("[bold blue]4. Writing components...[/bold blue]")
            generated_components = []
            for component in plan.components:
                try:
                    component_path = output_path / self.clean_path(component.path)
                    self.write_code_file(component_path, component.code)
                    generated_components.append(component_path)
                    
                    if component.test_code:
                        test_path = component_path.parent / "__tests__" / f"{component_path.stem}.test.tsx"
                        self.ensure_directory(test_path.parent)
                        self.write_code_file(test_path, component.test_code)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate component {component.name}: {str(e)}[/yellow]")
                    continue
            
            # Step 5: Write API routes following scaffold patterns
            self.console.print("[bold blue]5. Writing API routes...[/bold blue]")
            generated_routes = []
            for route in plan.api_routes:
                try:
                    route_path = output_path / "app/api" / self.clean_path(route.path) / "route.ts"
                    self.write_code_file(route_path, route.code)
                    generated_routes.append(route_path)
                    
                    if route.test_code:
                        test_path = route_path.parent / "__tests__" / "route.test.ts"
                        self.ensure_directory(test_path.parent)
                        self.write_code_file(test_path, route.test_code)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate route {route.path}: {str(e)}[/yellow]")
                    continue
            
            # Step 6: Write database files
            self.console.print("[bold blue]6. Writing database files...[/bold blue]")
            migrations_dir = output_path / "migrations"
            self.ensure_directory(migrations_dir)
            
            generated_migrations = []
            for i, migration in enumerate(plan.database.migrations):
                try:
                    migration_file = migrations_dir / f"{i + 1:04d}_{migration['name']}.sql"
                    if not migration.get("sql"):
                        raise ValueError(f"No SQL code for migration {migration['name']}")
                    self.write_file(migration_file, migration["sql"])
                    generated_migrations.append(migration_file)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate migration {migration['name']}: {str(e)}[/yellow]")
                    continue
            
            # Write database initialization
            try:
                db_init_path = output_path / "lib/db/init.ts"
                self.ensure_directory(db_init_path.parent)
                if not plan.database.initialization_code:
                    raise ValueError("No database initialization code generated")
                self.write_file(db_init_path, plan.database.initialization_code)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Failed to generate database initialization: {str(e)}[/yellow]")
            
            # Step 7: Write auth files following scaffold patterns
            self.console.print("[bold blue]7. Writing auth files...[/bold blue]")
            
            # Write middleware using scaffold pattern
            try:
                middleware_path = output_path / "middleware.ts"
                if not plan.auth.middleware:
                    raise ValueError("No middleware code generated")
                self.write_file(middleware_path, plan.auth.middleware)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Failed to generate middleware: {str(e)}[/yellow]")
            
            # Write auth components using scaffold patterns
            auth_dir = output_path / "components/auth"
            self.ensure_directory(auth_dir)
            generated_auth_components = []
            for component in plan.auth.components:
                try:
                    if not component.get("code"):
                        raise ValueError(f"No code for auth component {component['name']}")
                    self.write_file(auth_dir / f"{component['name']}.tsx", component["code"])
                    generated_auth_components.append(component['name'])
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate auth component {component['name']}: {str(e)}[/yellow]")
                    continue
            
            # Write auth utilities using scaffold patterns
            auth_utils_dir = output_path / "lib/auth"
            self.ensure_directory(auth_utils_dir)
            generated_auth_utils = []
            for name, code in plan.auth.utils.items():
                try:
                    if not code:
                        raise ValueError(f"No code for auth utility {name}")
                    self.write_file(auth_utils_dir / f"{name}.ts", code)
                    generated_auth_utils.append(name)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate auth utility {name}: {str(e)}[/yellow]")
                    continue
            
            # Step 8: Write configuration files from scaffold
            self.console.print("[bold blue]8. Writing configuration files...[/bold blue]")
            
            # Copy scaffold config files
            generated_configs = []
            for file_name, file_info in self.scaffold["structure"]["root"].get("config", {}).get("contents", {}).items():
                try:
                    if isinstance(file_info, dict) and "config" in file_info:
                        config_path = output_path / file_name
                        self.write_file(config_path, json.dumps(file_info["config"], indent=2))
                        generated_configs.append(file_name)
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Failed to generate config {file_name}: {str(e)}[/yellow]")
                    continue
            
            # Write package.json with scaffold dependencies
            try:
                package_json = {
                    "name": self.spec.project.name.lower().replace(" ", "-"),
                    "version": "0.1.0",
                    "private": True,
                    "scripts": {
                        "dev": "next dev",
                        "build": "next build",
                        "start": "next start",
                        "lint": "next lint",
                        "test": "jest"
                    },
                    "dependencies": self.scaffold["dependencies"],
                    "devDependencies": {
                        "@types/jest": "^29.0.0",
                        "@testing-library/react": "^14.0.0",
                        "@testing-library/jest-dom": "^6.0.0",
                        "jest": "^29.0.0",
                        "ts-jest": "^29.0.0"
                    }
                }
                self.write_file(output_path / "package.json", json.dumps(package_json, indent=2))
            except Exception as e:
                self.console.print(f"[yellow]Warning: Failed to generate package.json: {str(e)}[/yellow]")
            
            # Write environment variables from scaffold and spec
            try:
                env_vars = self.generate_environment_variables()
                env_content = "\n".join([f"{var}=" for var in env_vars.keys()])
                self.write_file(output_path / ".env.example", env_content)
                self.write_file(output_path / ".env", env_content)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Failed to generate environment files: {str(e)}[/yellow]")
            
            # Check if we generated enough files
            if not generated_files or not generated_components or not generated_routes:
                raise ValueError("Not enough files were generated successfully")
            
            return {
                "files": [f.dict() for f in plan.files],
                "components": [c.dict() for c in plan.components],
                "api_routes": [r.dict() for r in plan.api_routes],
                "migrations": plan.database.migrations,
                "auth": plan.auth.dict(),
                "generated": {
                    "files": len(generated_files),
                    "components": len(generated_components),
                    "routes": len(generated_routes),
                    "migrations": len(generated_migrations),
                    "auth_components": len(generated_auth_components),
                    "auth_utils": len(generated_auth_utils),
                    "configs": len(generated_configs)
                }
            }
            
        except Exception as e:
            self.console.print(f"[red]Error during code generation: {str(e)}[/red]")
            if output_path and output_path.exists():
                self.console.print("[yellow]Rolling back changes...[/yellow]")
                try:
                    shutil.rmtree(output_path)
                except Exception as cleanup_error:
                    self.console.print(f"[red]Error during cleanup: {str(cleanup_error)}[/red]")
            raise

    def generate_environment_variables(self) -> dict:
        """Generate environment variables configuration."""
        env_vars = {
            "NEXT_PUBLIC_SUPABASE_URL": "string",
            "NEXT_PUBLIC_SUPABASE_ANON_KEY": "string",
            "SUPABASE_SERVICE_ROLE_KEY": "string"
        }
        
        env_vars.update(self.spec.environmentVariables)
        
        if "auth" in self.spec.features:
            auth_features = self.spec.features["auth"]
            if "OAuth providers" in auth_features:
                env_vars.update({
                    "GOOGLE_CLIENT_ID": "string",
                    "GOOGLE_CLIENT_SECRET": "string",
                    "GITHUB_CLIENT_ID": "string",
                    "GITHUB_CLIENT_SECRET": "string"
                })
        
        return env_vars
