from lumos import lumos
from blueberry.models import Intent, ProjectSpec
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from codegen import Codebase
from codegen.extensions.langchain.agent import create_codebase_agent

class MasterAgent:
    def __init__(self):
        self.client = OpenAI()
        self.console = Console()

    def understand_intent(self, user_input: str) -> Intent:
        """Understand the user's intent from the user's input."""
        try:
            completion = self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze user requests for Next.js + Supabase applications and extract core features.
                        Focus on:
                        1. Core functionality and key features
                        2. Required auth/security features
                        3. Essential data models
                        4. Critical API endpoints"""
                    },
                    {"role": "user", "content": user_input}
                ],
                response_format=Intent
            )
            
            return completion.choices[0].message.parsed
            
        except Exception as e:
            raise ValueError(f"Failed to understand intent: {str(e)}")

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
        """Create a detailed project specification based on the intent and save it to a file."""
        try:
            spec = lumos.call_ai(
                messages=[
                    {
                        "role": "system",
                        "content": """Generate a detailed specification for a Next.js 14 + Supabase application.
                        Include:
                        1. React components with clear purposes
                        2. API routes with methods and auth requirements
                        3. Database tables with columns and relationships
                        4. Required environment variables
                        5. Pages with:
                           - Full paths (e.g. /dashboard, /profile)
                           - Associated API routes needed
                           - Required components
                           - Auth requirements
                           
                        
                        Keep the specification focused and practical."""
                    },
                    {
                        "role": "user",
                        "content": f"Generate specification for: {json.dumps(intent.model_dump(), indent=2)}"
                    }
                ],
                response_format=ProjectSpec,
                model="gpt-4o",
            )
            
            # Create specs directory if it doesn't exist
            os.makedirs("specs", exist_ok=True)
            
            # Save the spec to a file
            spec_file = os.path.join("specs", f"{spec.name.lower().replace(' ', '_')}_spec.json")
            with open(spec_file, "w") as f:
                json.dump(spec.model_dump(), f, indent=2)
            
            self.console.print(f"[green]✓ Specification saved to: {spec_file}[/green]")
            
            return spec
            
        except Exception as e:
            raise ValueError(f"Failed to create specification: {str(e)}")


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


class CodeAgent:
    def __init__(self, project_path: str, spec: ProjectSpec):
        self.console = Console()
        self.spec = spec
        self.project_path = os.path.abspath(project_path)
        
        try:
            self.codebase = Codebase(self.project_path)
            self.agent = create_codebase_agent(
                codebase=self.codebase,
                model_name="gpt-4o",
                temperature=0,
                verbose=True
            )
            self.supabase_agent = SupabaseSetupAgent(spec, self.project_path)
            self.console.print(f"[green]Successfully initialized CodeAgent at: {self.project_path}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error initializing CodeAgent: {str(e)}[/red]")
            raise

    def analyze_codebase(self) -> dict:
        """Analyze the current codebase structure and understand its components."""
        try:
            analysis_result = self.agent.invoke(
                {
                    "input": """Analyze the current Next.js 14 codebase and provide:
                    1. Current app router structure and pages
                    2. Existing components and their purposes
                    3. API routes and their functionality
                    4. Data models and database integration
                    5. Authentication setup if any
                    6. Utility functions and their usage"""
                },
                config={"configurable": {"session_id": "analyze_codebase"}}
            )
            
            self.console.print("[green]✓ Codebase analysis complete[/green]")
            return analysis_result
            
        except Exception as e:
            self.console.print(f"[red]Error analyzing codebase: {str(e)}[/red]")
            raise

    def implement_features(self) -> str:
        """Implement features according to the project specification."""
        try:
            # Analyze the codebase first
            analysis = self.analyze_codebase()
            
            # Read master prompt
            with open("prompts/master_prompt.md", "r") as f:
                master_prompt = f.read()
            
            # Use the agent to implement all features
            implementation_result = self.agent.invoke(
                {
                    "input": f"""Based on the codebase analysis:
                    {analysis}
                    
                    Master Prompt Guidelines:
                    {master_prompt}
                    
                    You are an expert full-stack developer implementing features in a Next.js 14 + Supabase application.
                    Assume that project structure exists already and you are adding files to it or modifying files.
                    
                    Implementation Order and Guidelines:

                    1. API Routes Implementation:
                       * Create all necessary API routes in app/api/ first
                       * Implement proper error handling and validation
                       * Set up Supabase queries and database interactions
                       * Add authentication middleware where needed
                       * Add TypeScript types for request/response
                    
                    2. Component Development:
                       * Create reusable components after API routes
                       * Use server components by default
                       * Create client components only when needed
                       * Implement loading and error states
                       * Style with Tailwind CSS
                       * Add TypeScript types and props validation
                    
                    3. Page Integration:
                       * Create pages last, using existing components and APIs
                       * Create a page.tsx file for each page in the spec
                       * Each page should:
                         - Import and use the relevant components
                         - Implement data fetching from API routes
                         - Add proper error boundaries and loading states
                         - Include metadata exports for SEO
                         - Follow app router conventions for layouts
                       * Create corresponding layout.tsx files where needed
                       * Implement proper navigation between pages
                       * Add loading.tsx and error.tsx for each route
                       * Ensure responsive design
                    
                    Project Structure:
                       * Work directly in app/ directory (NO src directory)
                       * Components in components/ directory
                       * API routes in app/api/
                       * Types in types/ directory
                       * Utils in lib/ directory
                       * Pages in app/ directory
                    
                    Code Quality:
                       * Verify files/folders exist before creating
                       * Use named imports instead of default imports
                       * Separate files logically
                       * Replace '_PLACEHOLDER_HERE_' with appropriate values
                       * Use relative paths for all operations
                       * Do not invent data that can be derived from existing code
                    
                    Project specification to implement:
                    {json.dumps(self.spec.model_dump(), indent=2)}
                    
                    Create or modify all necessary files following these guidelines."""
                },
                config={"configurable": {"session_id": "implement_features"}}
            )
            
            self.console.print("[green]✓ Features implemented successfully[/green]")
            return "Features implemented successfully"
            
        except Exception as e:
            self.console.print(f"[red]Error implementing features: {str(e)}[/red]")
            raise

    def transform_template(self) -> str:
        """Transform the template into the final application based on spec.
        This is the main entry point that coordinates the analysis and implementation."""
        try:
            # Set up Supabase first
            try:
                # Get credentials from spec if available
                project_ref = getattr(self.spec.supabaseConfig, 'projectRef', None) if hasattr(self.spec, 'supabaseConfig') else None
                anon_key = getattr(self.spec.supabaseConfig, 'anonKey', None) if hasattr(self.spec, 'supabaseConfig') else None
                service_key = getattr(self.spec.supabaseConfig, 'serviceKey', None) if hasattr(self.spec, 'supabaseConfig') else None
                
                # Setup will prompt for missing credentials
                self.supabase_agent.setup(project_ref, anon_key, service_key)
            except Exception as e:
                self.console.print(f"[red]Error setting up Supabase: {str(e)}[/red]")
                if not Confirm.ask("Would you like to continue with the rest of the implementation?"):
                    raise

            # # Then analyze the codebase
            # analysis = self.analyze_codebase()
            # self.console.print("\n[bold]Codebase Analysis:[/bold]")
            # self.console.print(analysis)

            # Then implement the features
            result = self.implement_features()
            
            self.console.print("\n[green]✓ Template transformation complete[/green]")
            return result
            
        except Exception as e:
            self.console.print(f"[red]Error transforming template: {str(e)}[/red]")
            raise

class SupabaseSetupAgent:
    def __init__(self, spec: ProjectSpec, project_path: str):
        self.spec = spec
        self.project_path = project_path
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
                        5. Do not include any RLS policies
                        
                        Format as a single SQL file with proper ordering of operations. dont include any other text no markdown, just code."""
                    },
                    {
                        "role": "user",
                        "content": f"Generate pgsql migration for: {json.dumps(self.spec.model_dump(), indent=2)}"
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
            subprocess.run(["npx", "supabase", "--version"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.console.print("[yellow]Supabase CLI not found. Installing...[/yellow]")
            subprocess.run(
                ["npm", "install", "supabase", "--save-dev"],
                cwd=self.project_path,
                check=True,
            )

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

        # Generate migration SQL
        migration_sql = self.get_migration_sql()
        
        # Set up project structure
        supabase_dir = Path(self.project_path) / "supabase"
        migrations_dir = supabase_dir / "migrations"
        config_file = supabase_dir / "config.toml"
        
        # Create directories
        migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Write migration file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        migration_file = migrations_dir / f"{timestamp}_initial_schema.sql"
        migration_file.write_text(migration_sql)

        try:
            # Initialize Supabase project if not already initialized
            if not config_file.exists():
                self.console.print("[yellow]Initializing Supabase project...[/yellow]")
                subprocess.run(
                    ["npx", "supabase", "init"],
                    cwd=self.project_path,
                    check=True,
                )

            # Login to Supabase
            self.console.print("[yellow]Logging in to Supabase...[/yellow]")
            subprocess.run(
                ["npx", "supabase", "login"],
                cwd=self.project_path,
                check=True,
            )

            # Link to remote project
            self.console.print(f"[yellow]Linking to Supabase project: {project_ref}[/yellow]")
            subprocess.run(
                [
                    "npx", "supabase", "link", 
                    "--project-ref", project_ref,
                    "--password", "",
                    "--debug"
                ],
                cwd=self.project_path,
                check=True,
            )

           
            
            # Push the migration
            self.console.print("[yellow]Pushing migration to remote database...[/yellow]")
            subprocess.run(
                ["npx", "supabase", "db", "push"],
                cwd=self.project_path,
                check=True,
            )
            
            self.console.print("[green]✅ Migration applied successfully[/green]")
            
        except subprocess.TimeoutExpired:
            raise Exception("Operation timed out while applying migration")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise Exception(f"Migration failed: {error_msg}")

    def setup_environment(self, project_ref: str, anon_key: str, service_key: str) -> None:
        """Set up environment variables for Supabase"""
        try:
            env_path = Path(self.project_path) / ".env.local"
            env_content = f"""NEXT_PUBLIC_SUPABASE_URL=https://{project_ref}.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY={anon_key}
SUPABASE_SERVICE_ROLE_KEY={service_key}
"""
            env_path.write_text(env_content)
            self.console.print("[green]✅ Environment variables set up successfully[/green]")
            
        except Exception as e:
            raise Exception(f"Failed to set up environment variables: {str(e)}")

    def _prompt_credentials(self) -> tuple[str, str, str]:
        """Prompt user for Supabase credentials if not in spec"""
        self.console.print("\n[bold yellow]Supabase Credentials Required[/bold yellow]")
        self.console.print("Please provide your Supabase project credentials:")
        
        project_ref = Prompt.ask(
            "\nProject Reference or URL",
            default=getattr(self.spec.supabaseConfig, 'projectRef', '') if hasattr(self.spec, 'supabaseConfig') else ''
        )
        
        anon_key = Prompt.ask(
            "Anon Key (public)",
            password=False,
        )
        
        service_key = Prompt.ask(
            "Service Role Key (secret)",
            password=True,
        )
        
        return project_ref, anon_key, service_key

    def setup(self, project_ref: str = None, anon_key: str = None, service_key: str = None) -> None:
        """Complete Supabase setup including migrations and environment variables"""
        try:
            self.console.print("[bold]Starting Supabase setup...[/bold]")
            
            # If any credentials are missing, prompt for all of them
            if not all([project_ref, anon_key, service_key]):
                project_ref, anon_key, service_key = self._prompt_credentials()
            
            # Apply database migrations
            self.apply_migration(project_ref, anon_key, service_key)
            
            # Set up environment variables
            self.setup_environment(project_ref, anon_key, service_key)
            
            self.console.print("[green bold]✅ Supabase setup completed successfully[/green bold]")
            
        except Exception as e:
            self.console.print(f"[red bold]❌ Supabase setup failed: {str(e)}[/red bold]")
            raise
