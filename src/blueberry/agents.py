from lumos import lumos
from blueberry.models import Intent, ProjectSpec, GeneratedCode, FileMode, FileContent, BuildError
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import re
from rich.progress import Progress
import traceback
from typing import List, Dict, Set
import shutil
import logging
from rich.logging import RichHandler
from rich.progress import SpinnerColumn, TextColumn
from rich.syntax import Syntax
import asyncio

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
    def __init__(self, project_path: str, spec: ProjectSpec):
        self.project_path = Path(project_path)
        self.spec = spec
        self.console = Console()
        self.existing_files = self._map_existing_files()
        self.current_dir = Path(__file__).parent
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.ai_log_file = log_dir / f"ai_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def _map_existing_files(self) -> Dict[str, Path]:
        """Map all existing files in the boilerplate"""
        files = {}
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(self.project_path))
                # Skip .git files
                if not relative_path.startswith('.git/'):
                    files[relative_path] = file_path
                    self.console.print(f"[dim]Found: {relative_path}[/dim]")
        return files

    def _log_ai_response(self, prompt: str, response: any, type: str = "generation"):
        """Log AI prompt and response"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.ai_log_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Type: {type}\n")
            f.write(f"\n--- Prompt ---\n")
            f.write(prompt)
            f.write(f"\n\n--- Response ---\n")
            if isinstance(response, (dict, list)):
                f.write(json.dumps(response, indent=2))
            else:
                f.write(str(response))
            f.write(f"\n{'='*80}\n")

    async def transform_template(self) -> bool:
        """Transform the boilerplate into the specified application"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            try:
                # 1. Generate structured code
                task = progress.add_task("[cyan]Generating code structure...", total=None)
                generated = await self._generate_structured_code()
                progress.update(task, completed=True)
                
                # 2. Apply changes safely
                task = progress.add_task("[cyan]Applying changes...", total=len(generated.files))
                for file in generated.files:
                    await self._apply_single_change(file)
                    progress.advance(task)
                
                # 3. Run build and fix errors
                task = progress.add_task("[cyan]Running build check...", total=None)
                if errors := await self._run_build():
                    self.console.print("\n[yellow]Found build errors, attempting repairs...[/yellow]")
                    await self._repair_code(errors)
                progress.update(task, completed=True)
                
                return True
                
            except Exception as e:
                self.console.print(f"[red]Error in code generation: {str(e)}[/red]")
                return False

    async def _generate_structured_code(self) -> GeneratedCode:
        """Generate code with structured output format"""
        core_prompt = (self.current_dir / "prompts" / "core_prompt.md").read_text()
        
        # Read existing migration file if it exists
        migration_file = self.project_path / "supabase" / "migrations"
        migration_sql = ""
        for file in migration_file.glob("*_initial_schema.sql"):
            migration_sql = file.read_text()
            break  # Take the first matching file
        
        prompt = f"""Based on the following project specification, generate or modify files for a Next.js 14 application.
        The application already has a basic structure with auth and Supabase integration.
        
        Project Spec:
        {self.spec.model_dump_json(indent=2)}
        
        Existing files structure:
        {self._get_files_structure()}
        
        Database Schema (Supabase):
        ```sql
        {migration_sql}
        ```
        
        Boilerplate Context:
        {core_prompt}
        
        Generate all the necessary new files (components, pages, api routes) or modifications to existing files.
        Make sure to:
        1. Use the exact table names and columns from the SQL schema
        2. Follow the database relationships defined in migrations
        3. Include proper type definitions for database tables
        4. Add proper error handling for database operations
        Do not regenerate unchanged boilerplate files.
        """

        response = await lumos.call_ai_async(
            messages=[
                {"role": "system", "content": "You are an expert Next.js developer..."},
                {"role": "user", "content": prompt}
            ],
            response_format=GeneratedCode,
            model="gpt-4o-mini"
        )
        
        # Log the raw response
        self._log_ai_response(prompt, response.model_dump(), "initial_generation")
        
        return response

    async def _apply_single_change(self, file: FileContent):
        """Apply a single file change"""
        try:
            relative_path = file.path.lstrip('/')
            full_path = self.project_path / relative_path
            
            self.console.print(f"[cyan]Processing: {relative_path}[/cyan]")
            
            # Create backup directory if needed
            backup_dir = self.project_path / ".backups"
            backup_dir.mkdir(exist_ok=True)
            
            if relative_path in self.existing_files:
                if file.mode == FileMode.MODIFY:
                    # Create backup
                    backup_path = backup_dir / f"{relative_path}.bak"
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, backup_path)
                    
                    # Modify file
                    full_path.write_text(file.content)
                    self.console.print(f"[yellow]Modified: {relative_path}[/yellow]")
            else:
                # New file
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(file.content)
                self.console.print(f"[green]Created: {relative_path}[/green]")

        except Exception as e:
            self.console.print(f"[red]Failed: {file.path} - {str(e)}[/red]")
            if 'backup_path' in locals() and backup_path.exists():
                shutil.copy2(backup_path, full_path)
                self.console.print(f"[yellow]Restored backup: {file.path}[/yellow]")

    async def _run_build(self) -> List[BuildError]:
        """Run next build and parse errors"""
        self.console.print("[cyan]Running build...[/cyan]")
        try:
            # First install dependencies if needed
            install_process = await asyncio.create_subprocess_exec(
                'npm', 'install',
                cwd=str(self.project_path),  # Explicitly convert Path to string
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await install_process.communicate()
            
            # Then run the build
            process = await asyncio.create_subprocess_exec(
                'npm', 'run', 'build',
                cwd=str(self.project_path),  # Explicitly convert Path to string
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                # Parse both stdout and stderr for errors
                errors = self._parse_build_errors(stdout.decode()) + self._parse_build_errors(stderr.decode())
                self.console.print(f"[yellow]Build failed with {len(errors)} errors[/yellow]")
                for error in errors:
                    self.console.print(f"[red]Error in {error.file}: {error.message}[/red]")
                return errors
            
            self.console.print("[green]Build completed successfully[/green]")
            return []
            
        except Exception as e:
            self.console.print(f"[red]Build process failed: {str(e)}[/red]")
            return []

    def _compile_error_patterns(self) -> dict:
        """Compile regex patterns for error parsing"""
        return {
            'typescript': re.compile(
                r'(?P<file>.*?)\((?P<line>\d+),(?P<column>\d+)\).*?: (?P<message>.*?)(?:\s+\((?P<code>TS\d+)\))?$'
            ),
            'module': re.compile(
                r"Cannot find module '(?P<module>[^']+)' from '(?P<file>[^']+)'"
            ),
            'import': re.compile(
                r"(?P<message>Import .+?) in (?P<file>.+?):(?P<line>\d+):(?P<column>\d+)"
            ),
            'nextjs': re.compile(
                r"(?:Error|error).*?: (?P<message>.+?)\s+Location: (?P<file>.+?):(?P<line>\d+):(?P<column>\d+)"
            ),
            'webpack': re.compile(
                r"Module build failed \(.*?\):\s*(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+)\s*(?P<message>.+)"
            ),
            'eslint': re.compile(
                r"(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+) - (?P<message>.+?) \[(?P<code>.+?)\]"
            )
        }

    def _parse_build_errors(self, output: str) -> List[BuildError]:
        """Parse build errors into structured format"""
        errors = []
        patterns = self._compile_error_patterns()
        
        # Split output into lines and process each line
        lines = output.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Try to find a file path in the line
            file_path_match = re.search(r'(?:\.\/|[a-zA-Z]:\\|\/)?(?:[\w\-. /\\]+\/)*([\w\-. ]+\.[a-zA-Z]+)', line)
            
            # Look for error patterns
            error_found = False
            for error_type, pattern in patterns.items():
                if match := pattern.search(line):
                    error_data = match.groupdict()
                    
                    # If file wasn't found in the pattern but we found one in the line
                    if error_data.get('file') == 'unknown' and file_path_match:
                        error_data['file'] = file_path_match.group(0)
                    
                    # Clean up the file path
                    if 'file' in error_data and error_data['file']:
                        error_data['file'] = error_data['file'].replace('\\', '/').strip()
                        # Remove ./ or / from the start of the path
                        error_data['file'] = re.sub(r'^\.?/', '', error_data['file'])
                    
                    errors.append(BuildError(
                        file=error_data.get('file', 'unknown'),
                        message=error_data.get('message', line).strip(),
                        type=error_type,
                        line=int(error_data.get('line', 0)),
                        column=int(error_data.get('column', 0)),
                        code=error_data.get('code', '')
                    ))
                    error_found = True
                    break
            
            # If no pattern matched but line contains error-like content
            if not error_found and ('Error:' in line or 'error' in line.lower()):
                # Look ahead a few lines for a file path
                for j in range(i + 1, min(i + 4, len(lines))):
                    file_path_match = re.search(r'(?:\.\/|[a-zA-Z]:\\|\/)?(?:[\w\-. /\\]+\/)*([\w\-. ]+\.[a-zA-Z]+)', lines[j])
                    if file_path_match:
                        file_path = file_path_match.group(0).replace('\\', '/').strip()
                        file_path = re.sub(r'^\.?/', '', file_path)
                        errors.append(BuildError(
                            file=file_path,
                            message=line.strip(),
                            type='generic',
                            line=0,
                            column=0,
                            code=''
                        ))
                        error_found = True
                        break
                
                # If still no file path found, add as unknown
                if not error_found:
                    errors.append(BuildError(
                        file='unknown',
                        message=line.strip(),
                        type='generic',
                        line=0,
                        column=0,
                        code=''
                    ))
            
            i += 1
        
        return errors

    async def _repair_code(self, errors: List[BuildError]):
        """Fix build errors using AI"""
        for error in errors:
            if error.file == 'unknown':
                continue

            file_path = self.project_path / error.file
            if not file_path.exists():
                continue

            current_content = file_path.read_text()
            
            prompt = f"""Fix this build error in a Next.js 14 application:
            
            File: {error.file}
            Type: {error.type}
            Message: {error.message}
            Line: {error.line}
            Column: {error.column}
            Error Code: {error.code}
            
            Current content:
            {current_content}
            
            Please provide only the corrected code without any explanation.
            """

            try:
                fixed_content = await lumos.call_ai_async(
                    messages=[
                        {"role": "system", "content": "You are an expert Next.js TypeScript developer..."},
                        {"role": "user", "content": prompt}
                    ],
                    model="gpt-4o-mini"
                )
                
                # Create backup
                backup_dir = self.project_path / ".backups"
                backup_path = backup_dir / f"{error.file}.error.bak"
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
                
                # Apply fix
                file_path.write_text(fixed_content)
                self.console.print(f"[green]Fixed error in {error.file}[/green]")
                
            except Exception as e:
                self.console.print(f"[red]Failed to fix {error.file}: {str(e)}[/red]")
                if 'backup_path' in locals() and backup_path.exists():
                    shutil.copy2(backup_path, file_path)
                    self.console.print(f"[yellow]Restored backup for {error.file}[/yellow]")

    def _get_files_structure(self) -> str:
        """Get a string representation of existing files structure"""
        return "\n".join(sorted(self.existing_files.keys()))


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
                        2. Functions and triggers for linking auth.users to the users table
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
            # Generate migration SQL first
            migration_sql = self.get_migration_sql()
            
            # Create migrations directory
            migrations_dir = Path(self.project_path) / "supabase" / "migrations"
            migrations_dir.mkdir(parents=True, exist_ok=True)
            
            # Write migration file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            migration_file = migrations_dir / f"{timestamp}_initial_schema.sql"
            migration_file.write_text(migration_sql)
            
            # Check for Supabase CLI
            try:
                subprocess.run(["npx", "supabase", "--version"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.console.print("[yellow]Supabase CLI not found. Installing...[/yellow]")
                subprocess.run(
                    ["npm", "install", "supabase", "--save-dev"],
                    cwd=self.project_path,
                    check=True,
                )

            # Extract project ref from URL if provided
            clean_project_ref = project_ref
            if "supabase.co" in project_ref:
                clean_project_ref = project_ref.split("//")[1].split(".")[0]

            # Validate project ref format
            if not clean_project_ref.isalnum() or len(clean_project_ref) != 20:
                raise Exception("Invalid project ref format. Must be a 20-character alphanumeric string.")

            # Check for config file
            config_file = Path(self.project_path) / "supabase" / "config.toml"
            
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
            self.console.print(f"[yellow]Linking to Supabase project: {clean_project_ref}[/yellow]")
            subprocess.run(
                [
                    "npx", "supabase", "link", 
                    "--project-ref", clean_project_ref,
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
            # Extract project reference from URL if needed
            if "supabase.co" in project_ref:
                project_ref = project_ref.split("//")[1].split(".")[0]

            # Create .env.local with correct Supabase environment variables
            env_content = f"""NEXT_PUBLIC_SUPABASE_URL=https://{project_ref}.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY={anon_key}
SUPABASE_SERVICE_ROLE_KEY={service_key}
"""
            env_path = Path(self.project_path) / ".env.local"
            
            # Create backup if file exists
            if env_path.exists():
                backup_path = Path(self.project_path) / ".env.local.bak"
                shutil.copy2(env_path, backup_path)
                self.console.print("[yellow]Created backup of existing .env.local[/yellow]")

            # Write new .env.local file
            env_path.write_text(env_content)
            self.console.print("[green]✅ Environment variables set up successfully in .env.local[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Failed to set up environment variables: {str(e)}[/red]")
            # Restore backup if it exists
            if 'backup_path' in locals() and backup_path.exists():
                shutil.copy2(backup_path, env_path)
                self.console.print("[yellow]Restored backup of .env.local[/yellow]")
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
