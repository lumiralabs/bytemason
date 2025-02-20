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

class ProjectBuilder:
    def __init__(self):
        self.console = Console()

    def understand_intent(self, user_input: str) -> Intent:
        """Understand the user's intent from the user's input."""
        try:
            intent = lumos.call_ai(
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze user requests for Next.js 14 + Supabase applications and extract core features.
                        Focus on:
                        1. Core functionality and key features
                        2. Required auth/security features
                        3. Essential data models
                        4. Critical API endpoints
                        5. Keep it simple and practical, dont add any fancy features.
                        """
                    },
                    {"role": "user", "content": user_input}
                ],
                response_format=Intent,
                model="gpt-4o-mini",
            )
            
            return intent
            
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
        
        return feature

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
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, "prompts", "core_prompt.md")
            
            with open(prompt_path, 'r') as f:
                core_prompt = f.read()

            spec = lumos.call_ai(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Generate a detailed specification for a Next.js 14 App router + Supabase application.

                        You currently have a boilerplate with all the basic setup done, you just need to add the features requested by the user.
                        {core_prompt}

                        Include:
                        1. components with clear purposes
                        2. API routes for all the operations needed
                        3. Postgres database tables with columns and relationships
                        4. Pages with:
                           - Full paths (e.g. /dashboard, /profile)
                           - Associated API routes needed
                           - Required components
                           - Auth requirements
                           
                        
                        Keep the specification simple and practical. Dont add any fancy features. """
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

    def setup_supabase(self, spec: ProjectSpec) -> bool:
        """Set up Supabase configuration and database for the project.
        
        Args:
            spec: The project specification containing Supabase configuration
            
        Returns:
            bool: True if setup was successful or user chose to continue, False if setup failed and user chose to abort
        """
        try:
            # Get credentials from spec if available
            project_ref = getattr(spec.supabaseConfig, 'projectRef', None) if hasattr(spec, 'supabaseConfig') else None
            anon_key = getattr(spec.supabaseConfig, 'anonKey', None) if hasattr(spec, 'supabaseConfig') else None
            service_key = getattr(spec.supabaseConfig, 'serviceKey', None) if hasattr(spec, 'supabaseConfig') else None
            
            # Create Supabase agent and run setup
            supabase_agent = SupabaseSetupAgent(spec, os.getcwd())
            supabase_agent.setup(project_ref, anon_key, service_key)
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error setting up Supabase: {str(e)}[/red]")
            if not Confirm.ask("Would you like to continue with the rest of the implementation?"):
                return False
            return True



class CodeAgent:
    # TODO: Implement code generation agent
    pass


class SupabaseSetupAgent:
    def __init__(self, spec: ProjectSpec, project_path: str):
        self.spec = spec
        self.project_path = project_path
        self.console = Console()
        
    def get_migration_sql(self) -> str:
        """Generate SQL migration based on the spec"""
        try:
            migrations = lumos.call_ai(
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
                model="gpt-4o-mini",
            )
            return migrations
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
