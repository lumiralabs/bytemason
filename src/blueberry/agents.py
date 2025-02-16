from lumos import lumos
from blueberry.models import Intent, ProjectSpec
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
import json
import os
from openai import OpenAI
from typing import Dict
from pathlib import Path
import shutil
import subprocess
from datetime import datetime


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
                        "content": """You are an expert full-stack developer specializing in Next.js 14 app router and Supabase applications. Generate a detailed specification for a web application based on the user's prompt.
                        
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
                        1. Always include supabase authentication and authorization
                        2. Use TypeScript and modern React patterns
                        3. Implement proper security measures
                        4. Consider performance optimizations
                        5. Follow Next.js app router best practices for routing and data fetching
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


class CodeGeneratorAgent:
    def __init__(self, spec: ProjectSpec):
        self.spec = spec
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI()
        self.console = Console()
        self.project_dir = Path.cwd() / self.spec.project.name
        self.boilerplate_path = Path(__file__).parent.parent.parent / "boilerplate"
        self.scaffold_path = self.boilerplate_path / "scaffold.json"

    def setup_project(self) -> None:
        """Clone boilerplate and set up the new project directory"""
        self.console.log(f'🚀 Creating new project: {self.spec.project.name}')
        
        try:
            # Remove existing directory if it exists
            if self.project_dir.exists():
                shutil.rmtree(self.project_dir)
            
            # Copy boilerplate to new project directory
            shutil.copytree(self.boilerplate_path, self.project_dir)
            
            # Update package.json with project name
            package_json_path = self.project_dir / "package.json"
            if package_json_path.exists():
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                package_data["name"] = self.spec.project.name
                with open(package_json_path, 'w') as f:
                    json.dump(package_data, f, indent=2)
                    
            self.console.log('✅ Project directory created successfully')
            
        except Exception as e:
            self.console.log('💥 Failed to set up project directory:', str(e))
            raise

    def write_files(self, files: Dict[str, str]) -> None:
        """Write generated files to the project directory"""
        self.console.log('📝 Writing generated files...')
        
        try:
            for file_path, content in files.items():
                full_path = self.project_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w') as f:
                    f.write(content)
                    
            self.console.log('✅ Files written successfully')
            
        except Exception as e:
            self.console.log('💥 Failed to write files:', str(e))
            raise

    def install_dependencies(self) -> None:
        """Install project dependencies"""
        self.console.log('📦 Installing dependencies...')
        
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
                text=True
            )
            self.console.log('✅ Dependencies installed successfully')
            
        except subprocess.CalledProcessError as e:
            self.console.log('💥 Failed to install dependencies:', e.stderr)
            raise

    def get_supabase_credentials(self) -> tuple:
        """Get Supabase credentials from user"""
        console = Console()
        
        console.print("\n[bold blue]🔑 Please provide your Supabase credentials[/bold blue]")
        console.print("[dim]You can find these in Project Settings > API > Project API keys[/dim]\n")
        
        project_input = Prompt.ask(
            "\nProject Reference ID or URL (e.g., https://xxx.supabase.co or project-id)"
        )
        
        anon_key = Prompt.ask(
            "\nAnon/Public Key"
        )
        
        service_key = Prompt.ask(
            "\nService Role Key",
            password=True  # Hide the service key input
        )
        
        return project_input, anon_key, service_key

    def generate_project(self) -> None:
        """Complete project generation workflow"""
        try:
            # Step 1: Set up project directory
            self.setup_project()
            
            # Step 2: Ask for Supabase setup BEFORE generating files
            supabase_credentials = None
            if Confirm.ask("\nWould you like to set up Supabase database now?"):
                try:
                    project_ref, anon_key, service_key = self.get_supabase_credentials()
                    supabase_credentials = (project_ref, anon_key, service_key)
                except Exception as e:
                    self.console.print(f"\n[red]Error getting Supabase credentials: {str(e)}[/red]")
                    if not Confirm.ask("\nWould you like to continue with code generation anyway?"):
                        raise
            
            # Step 3: Generate code files
            self.console.log('🎨 Generating code files...')
            files = self.generate_code()
            
            # Step 4: Write files
            self.write_files(files)
            
            # Step 5: Apply Supabase migrations if we have credentials
            if supabase_credentials:
                try:
                    project_ref, anon_key, service_key = supabase_credentials
                    supabase_agent = SupabaseSetupAgent(self.spec)
                    supabase_agent.apply_migration(project_ref, anon_key, service_key)
                except Exception as e:
                    self.console.print(f"\n[red]Error setting up Supabase: {str(e)}[/red]")
                    if not Confirm.ask("\nWould you like to continue anyway?"):
                        raise
            
            # Step 6: Install dependencies
            self.install_dependencies()
            
            # Final success message
            self.console.print(f"""
[bold green]🎉 Project generated successfully![/bold green]

Your project is ready at: {self.project_dir}

To get started:
1. cd {self.spec.project.name}
2. npm run dev

Happy coding! 🚀
            """)
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Project generation failed: {str(e)}[/bold red]")
            raise

    def generate_code(self) -> Dict[str, str]:
        """Generate code files based on the specification"""
        self.console.log('🚀 [Code Generation] Processing specification...')
        
        try:
            self.console.log('📡 [Code Generation] Making OpenAI API call...')
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f""" You are an expert Next.js developer. Generate a JSON object containing all necessary code files for a Next.js application based on the provided specification.

                        The response must be a valid JSON object where:
                        - Keys are file paths
                        - Values are the complete file contents
                        
                        Example JSON structure:
                        {{
                            "app/page.tsx": "content of home page",
                            "app/layout.tsx": "content of root layout",
                            "components/ui/button.tsx": "content of button component",
                            "lib/utils.ts": "content of utilities"
                        }}                        

                        Guidelines:
                        1. Use Next.js 14 App Router
                        2. Include TypeScript types
                        3. Use Tailwind CSS for styling
                        4. Implement proper error handling
                        5. Follow modern React patterns
                        6. Include necessary comments
                        7. Generate complete, working code
                        8. Include proper imports
                        
                        Required files in JSON response:
                        - app/page.tsx (home page)
                        - app/layout.tsx (root layout)
                        - app/api/route.ts (API routes)
                        - components/ui/* (UI components)
                        - libs/supabase.ts (Supabase client)
                        - types/index.ts (TypeScript types)
                        
                        {json.dumps(self.scaffold_path.read_text(), indent=2)}
                        """
                    },
                    {
                        "role": "user",
                        "content": f"Generate a JSON object containing all code files for this specification: {json.dumps(self.spec.model_dump(), indent=2)}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            self.console.log('✅ [Code Generation] OpenAI API call successful')

            message = completion.choices[0].message
            if not message.content:
                self.console.log('❌ [Code Generation] No valid response from OpenAI')
                raise ValueError("Failed to generate code: Empty response from OpenAI")

            try:
                files = json.loads(message.content)
                self.console.log('✨ [Code Generation] Parsed JSON response')
                return files

            except json.JSONDecodeError as e:
                self.console.log('💥 [Code Generation] Failed to parse JSON response')
                raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")

        except Exception as e:
            self.console.log('💥 [Code Generation] Error:', str(e))
            raise


class SupabaseSetupAgent:
    def __init__(self, spec: ProjectSpec):
        self.spec = spec
        self.client = OpenAI()
        self.console = Console()
        
    def get_migration_sql(self) -> str:
        """Generate SQL migration based on the spec"""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Generate a complete pgsql migration for Supabase based on the specification.
                        Include:
                        1. Table creation with proper types and constraints
                        2. Functions and triggers if any
                        3. Indexes if any
                        4. Initial seed data if needed
                        
                        Format as a single SQL file with proper ordering of operations. dont include any other text no markdown, just code."""
                    },
                    {
                        "role": "user",
                        "content": f"Generate pgsql migration for: {json.dumps(self.spec.supabaseConfig.model_dump(), indent=2)}"
                    }
                ],
                timeout=30
            )
            return completion.choices[0].message.content
        except Exception as e:
            self.console.print(f"[red]Failed to generate SQL migration: {e}[/red]")
            raise
            
    def apply_migration(self, project_ref: str, anon_key: str, service_key: str) -> None:
        """Apply migration to Supabase project"""
        try:
            # Check for Supabase CLI
            subprocess.run(["supabase", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("Supabase CLI not found. Please install it first: https://supabase.com/docs/guides/cli")

        # Extract project ref from URL if needed
        if "supabase.co" in project_ref:
            try:
                # Extract the project reference from URL
                project_ref = project_ref.split("//")[1].split(".")[0]
            except IndexError:
                raise Exception("Invalid Supabase project URL format")

        # Validate project ref format
        if not project_ref.isalnum() or len(project_ref) != 20:
            raise Exception("Invalid project ref format. Must be a 20-character alphanumeric string.")

        migration_sql = self.get_migration_sql()
        migrations_dir = Path.cwd() / self.spec.project.name / "supabase" / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        migration_file = migrations_dir / f"{timestamp}_initial_setup.sql"
        migration_file.write_text(migration_sql)

        try:
            # Initialize Supabase project if not already initialized
            if not (migrations_dir.parent / "config.toml").exists():
                self.console.print("[yellow]Initializing Supabase project...[/yellow]")
                subprocess.run(
                    ["supabase", "init"],
                    cwd=migrations_dir.parent.parent,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

            # Link the project
            self.console.print(f"[yellow]Linking to Supabase project: {project_ref}[/yellow]")
            subprocess.run(
                [
                    "supabase", "link", 
                    "--project-ref", project_ref,
                    "--password", service_key
                ],
                cwd=migrations_dir.parent.parent,
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Push the migration
            self.console.print("[yellow]Pushing migration...[/yellow]")
            subprocess.run(
                ["supabase", "db", "push"],
                cwd=migrations_dir.parent.parent,
                check=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.console.print("[green]✅ Migration applied successfully[/green]")
            
        except subprocess.TimeoutExpired:
            raise Exception("Operation timed out while applying migration")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise Exception(f"Migration failed: {error_msg}")
