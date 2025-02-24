from lumos import lumos
from blueberry.models import (
    Intent,
    ProjectSpec,
    GeneratedCode,
    FileMode,
    FileContent,
    BuildError,
    BuildErrorReport
)
from rich.console import Console
from rich.prompt import Prompt
import typer
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
import re
from rich.progress import Progress
from typing import List, Dict
import shutil
from rich.progress import SpinnerColumn, TextColumn
import asyncio
from fnmatch import fnmatch
from blueberry.repair_agent import RepairAgent


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
                        "content": """Yor are a senior product planner who creates a detailed requirement analysis and creates a list of important features, you don't do in fancy less useful features you just focus on core features. 
                        Analyze user requests for typescript, Next.js 14 app router + Supabase applications and extract core features.
                        Focus on:
                        1. Core functionality and key features
                        2. Required auth/security features
                        3. Essential data models
                        4. Critical API endpoints
                        5. Keep it simple and practical, dont add any fancy features.
                        """,
                    },
                    {"role": "user", "content": user_input},
                ],
                response_format=Intent,
                model="gpt-4o",
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

        _intent = lumos.call_ai(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": f"Enhance this feature: {feature}"},
            ],
            response_format=Intent,
            model="gpt-4o",
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

            if not typer.confirm(
                "\nWould you like to modify these features?",
                default=False,
                show_default=True,
            ):
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
                if typer.confirm(
                    "Would you like AI to validate and enhance this feature?",
                    default=True,
                    show_default=True,
                ):
                    status = console.status("[bold green]Validating feature...")
                    status.start()
                    try:
                        enhanced_feature = self.validate_feature(new_feature)
                        if enhanced_feature != new_feature:
                            status.stop()
                            if typer.confirm(
                                f"Would you like to use the enhanced version: {enhanced_feature}?",
                                default=True,
                                show_default=True,
                            ):
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

                remove_idx = (
                    int(
                        Prompt.ask(
                            "Enter number of feature to remove",
                            choices=[
                                str(i) for i in range(1, len(intent.features) + 1)
                            ],
                        )
                    )
                    - 1
                )
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

            with open(prompt_path, "r") as f:
                core_prompt = f.read()

            spec = lumos.call_ai(
                messages=[
                    {
                        "role": "system",
                        "content": f""" You are a senior NextJS 14 + Supabase developer, you know the complexities of developing different parts and features of an app, you don't just start writing, 
                        you do a risk and feasibility analysis first and then come up with a detailed specification of the whole app, you know that every single word you write will impact how the junior devs will think so you try to be as precise and descriptive as possible.
                        Generate a detailed specification for a Next.js 14 App router + Supabase application.

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
                           
                        
                        Keep the specification simple and practical. Dont add any fancy features. """,
                    },
                    {
                        "role": "user",
                        "content": f"Generate specification for: {json.dumps(intent.model_dump(), indent=2)}",
                    },
                ],
                response_format=ProjectSpec,
                model="gpt-4o",
            )

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
            project_ref = (
                getattr(spec.supabaseConfig, "projectRef", None)
                if hasattr(spec, "supabaseConfig")
                else None
            )
            anon_key = (
                getattr(spec.supabaseConfig, "anonKey", None)
                if hasattr(spec, "supabaseConfig")
                else None
            )
            service_key = (
                getattr(spec.supabaseConfig, "serviceKey", None)
                if hasattr(spec, "supabaseConfig")
                else None
            )

            # Create Supabase agent and run setup
            supabase_agent = SupabaseSetupAgent(spec, os.getcwd())
            supabase_agent.setup(project_ref, anon_key, service_key)
            return True

        except Exception as e:
            self.console.print(f"[red]Error setting up Supabase: {str(e)}[/red]")
            if not typer.confirm(
                "Would you like to continue with the rest of the implementation?",
                default=False,
                show_default=True,
            ):
                return False
            return True


class CodeAgent:
    def __init__(self, project_path: str, spec: ProjectSpec, ignore_patterns: List[str] = None):
        self.project_path = Path(project_path)
        self.spec = spec
        self.console = Console()
        self.ignore_patterns = ignore_patterns or []
        self.existing_files = self._map_existing_files()
        self.current_dir = Path(__file__).parent
        self.repair_agent = RepairAgent(project_path)

        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.ai_log_file = (
            log_dir / f"ai_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored based on ignore patterns"""
        return any(fnmatch(path, pattern) for pattern in self.ignore_patterns)

    def _map_existing_files(self) -> Dict[str, Path]:
        """Map all existing files in the boilerplate"""
        files = {}
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(self.project_path))
                # Skip .git files and ignored patterns
                if not relative_path.startswith(".git/") and not self._should_ignore(relative_path):
                    files[relative_path] = file_path
                    self.console.print(f"[dim]Found: {relative_path}[/dim]")
        return files

    def _log_ai_response(self, prompt: str, response: any, type: str = "generation"):
        """Log AI prompt and response"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.ai_log_file, "a") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Type: {type}\n")
            f.write("\n--- Prompt ---\n")
            f.write(prompt)
            f.write("\n\n--- Response ---\n")
            if isinstance(response, (dict, list)):
                f.write(json.dumps(response, indent=2))
            else:
                f.write(str(response))
            f.write(f"\n{'=' * 80}\n")

    async def transform_template(self) -> bool:
        """Transform the boilerplate into the specified application"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            try:
                # 1. Generate structured code
                task = progress.add_task(
                    "[cyan]Generating code structure...", total=None
                )
                generated = await self._generate_structured_code()
                progress.update(task, completed=True)

                # 2. Apply changes safely
                task = progress.add_task(
                    "[cyan]Applying changes...", total=len(generated.files)
                )
                for file in generated.files:
                    await self._apply_single_change(file)
                    progress.advance(task)

                # 3. Run build and fix errors
                task = progress.add_task("[cyan]Running build check...", total=None)
                if errors := await self._run_build():
                    self.console.print(
                        "\n[yellow]Found build errors, attempting repairs...[/yellow]"
                    )
                    await self._repair_code(errors)
                progress.update(task, completed=True)

                return True

            except Exception as e:
                self.console.print(f"[red]Error in code generation: {str(e)}[/red]")
                return False

    async def _generate_structured_code(self) -> GeneratedCode:
        """Generate code with maximum context flow: API -> Components -> Pages"""
        all_files = []
        
        # Get core prompt
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir, "prompts", "core_prompt.md"), "r") as f:
            core_prompt = f.read()
        
        # 1. Generate API routes first
        api_files = await self._generate_api_routes(core_prompt)
        all_files.extend(api_files)
        
        # 2. Generate components with API context
        component_files = await self._generate_components(core_prompt, api_files)
        all_files.extend(component_files)
        
        # 3. Generate pages with full context
        page_files = await self._generate_pages(core_prompt, api_files, component_files)
        all_files.extend(page_files)
        
        return GeneratedCode(files=all_files)

    async def _generate_api_routes(self, core_prompt: str) -> List[FileContent]:
        """Generate all API routes with database context"""
        prompt = f"""As a Next.js 14 Route Handler specialist, generate all API routes.

        Critical Requirements:
        1. Use Route Handlers (app/api/*/route.ts), NOT pages/api
        2. Each handler must:
           - Use proper HTTP methods (GET, POST, PUT, DELETE)
           - Have proper TypeScript types for request/response
           - Include error handling with appropriate status codes
           - don't use any ORM, just use the normal supabase client
        3. Follow these patterns:
           - Use NextResponse from 'next/server'
           - Handle authentication via middleware (already implemented)
           - Include proper CORS headers where needed
           - Use edge runtime where beneficial
        4. Security considerations:
           - Validate all inputs
           - Check user permissions
           - Sanitize responses
           - Handle rate limiting

        Example Route Handler Structure:

        ```typescript
        import {{ NextResponse }} from 'next/server'
        import {{ createClient }} from '@/libs/supabase/server';

        export async function POST(req: Request) {{
          try {{
            const supabase = createClient();
            const {{ data: {{ session }} }} = await supabase.auth.getSession();
            const body = await request.json();
            // Handler logic
            const data = await supabase
            .from('table_name')
            .select('*')
            .eq('id', body.id)
            .single();

            return NextResponse.json(data);
          }} catch (error) {{
            return NextResponse.json(
              {{ error: 'Validation failed' }},
              {{ status: 400 }}
            )
          }}
        }}
        ```

        Spec:
        {json.dumps(self.spec.model_dump(), indent=2)}
        
        {core_prompt}
        """
        
        return (await lumos.call_ai_async(
            messages=[
                {"role": "system", "content": "You are a Next.js 14 Route Handler specialist focusing on type-safety and security."},
                {"role": "user", "content": prompt}
            ],
            response_format=GeneratedCode,
            model="gpt-4o"
        )).files


    async def _generate_components(self, core_prompt: str, api_files: List[FileContent]) -> List[FileContent]:
        """Generate components with API context"""
        api_context = "\n\n".join(f"// {f.path}\n{f.content}" for f in api_files)
        
        prompt = f"""As a Next.js 14 Component architect, generate all React components.

        Critical Requirements:
        1. Component Location:
           - ALL components MUST be in components/ directory
           - Group by feature (e.g., components/todos/, components/profile/)
           - NO components in app/ directory
           
        2. Component Architecture:
           - Server Components by default (no "use client" unless needed)
           - Client Components only for:
             * Interactivity (onClick, onChange)
             * Browser APIs
             * React hooks
             * Client state
           - Use shadcn/ui components from @/components/ui/
           
        3. Data Handling:
           - Use Server Components for data fetching
           - Use createClient() from '@/libs/supabase/server' for server components
           - Use createClient() from '@/libs/supabase/client' for client components
           - Implement proper loading states
           - Handle errors gracefully
           
        Example Component Structure:
        ```typescript
        // components/todos/TodoList.tsx
        import {{ createClient }} from '@/libs/supabase/server'
        import {{ Button }} from '@/components/ui/button'

        interface TodoListProps {{
          initialTodos?: Todo[]
        }}

        export default async function TodoList({{ props }}: TodoListProps) {{
          const supabase = createClient()
          // Component logic
        }}
        ```

        Available Route Handlers:
        {api_context}

        Spec:
        {json.dumps(self.spec.model_dump(), indent=2)}
        
        {core_prompt}
        """
        
        return (await lumos.call_ai_async(
            messages=[
                {"role": "system", "content": "You are a Next.js 14 Component architect specializing in Server and Client Components."},
                {"role": "user", "content": prompt}
            ],
            response_format=GeneratedCode,
            model="gpt-4o"
        )).files

    async def _generate_pages(
        self, 
        core_prompt: str,
        api_files: List[FileContent],
        component_files: List[FileContent]
    ) -> List[FileContent]:
        """Generate pages with full context"""
        context = {
            'api': "\n\n".join(f"// {f.path}\n{f.content}" for f in api_files),
            'components': "\n\n".join(f"// {f.path}\n{f.content}" for f in component_files)
        }
        
        prompt = f"""As a Next.js 14 App Router specialist, generate all pages.

        Critical Requirements:
        1. File Structure:
           - Use app/[route]/page.tsx for pages
           - Include layout.tsx for shared UI
           - Add loading.tsx for suspense in root directory app/loading.tsx
           - Add error.tsx for error handling in root directory app/error.tsx
           - Use not-found.tsx for 404s in root directory app/not-found.tsx
           - Make a landing page in the root of the app app/page.tsx
           
        2. Page Architecture:
           - Server Components by default
           - Import components from @/components/
           - Use proper metadata exports
           - Implement proper auth checks
           
        3. Data Flow:
           - Fetch data in Server Components
           - Pass data down as props
           - Use suspense boundaries
           - Handle loading states
           
        4. Routing & Layout:
           - Use proper route grouping
           - Handle dynamic segments
           - Use proper navigation patterns
           - Use useRouter for navigation imported from next/navigation
           - Use createClient() from '@/libs/supabase/server'

        Example Page Structure:
        ```typescript
       
        import {{ createClient }} from '@/libs/supabase/server'
        import {{ TodoList }} from '@/components/todos/TodoList'
        
        
        export default async function DashboardPage() {{
          const supabase = createClient()
          // Page logic
          return <TodoList />
        }}
        ```

        Available Components:
        {context['components']}

        Available Route Handlers:
        {context['api']}

        Spec:
        {json.dumps(self.spec.model_dump(), indent=2)}
        
        {core_prompt}
        """
        
        return (await lumos.call_ai_async(
            messages=[
                {"role": "system", "content": "You are a Next.js 14 App Router specialist focusing on proper page structure and data flow."},
                {"role": "user", "content": prompt}
            ],
            response_format=GeneratedCode,
            model="gpt-4o"
        )).files

    async def _apply_single_change(self, file: FileContent):
        """Apply a single file change"""
        try:
            relative_path = file.path.lstrip("/")
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
            if "backup_path" in locals() and backup_path.exists():
                shutil.copy2(backup_path, full_path)
                self.console.print(f"[yellow]Restored backup: {file.path}[/yellow]")

    async def _run_build(self) -> List[BuildError]:
        """Run next build and parse errors"""
        self.console.print("[cyan]Running build...[/cyan]")
        try:
            # First install dependencies if needed
            install_process = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await install_process.communicate()

            # Then run the build with detailed error reporting
            process = await asyncio.create_subprocess_exec(
                "npm",
                "run",
                "build",
                "--no-color",  # Disable colors for cleaner output
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"}  # Disable telemetry
            )
            stdout, stderr = await process.communicate()
            
            # Combine stdout and stderr for complete error capture
            full_output = stdout.decode() + "\n" + stderr.decode()
            
            if process.returncode != 0:
                # First try AI-powered error analysis
                try:
                    errors = await self._analyze_build_errors_with_ai(full_output)
                    if errors:
                        self.console.print(f"[yellow]Build failed with {len(errors.errors)} errors[/yellow]")
                        for error in errors.errors:
                            self.console.print(f"[red]Error in {error.file}: {error.message}[/red]")
                        return errors.errors
                except Exception as e:
                    self.console.print(f"[yellow]AI error analysis failed, falling back to basic parsing: {str(e)}[/yellow]")
                return errors

        except Exception as e:
            self.console.print(f"[red]Build process failed: {str(e)}[/red]")
            return []

    async def _analyze_build_errors_with_ai(self, build_output: str) -> BuildErrorReport:
        """Use AI to analyze build errors more intelligently"""
        try:
            prompt = f"""Analyze this Next.js build output and extract all errors.
            For each error, identify:
            1. The file path (relative to project root)
            2. The error message
            3. The error type (typescript, runtime, etc)
            4. Line and column numbers if available
            5. Any relevant error code

            Build Output:
            {build_output}"""

            response = await lumos.call_ai_async(
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing Next.js and TypeScript build errors."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4o",
                response_format=BuildErrorReport
            )

            print(response);


            return response

        except Exception as e:
            self.console.print(f"[yellow]AI error analysis failed: {str(e)}[/yellow]")
            return []

    def _parse_build_output(self, output: str) -> List[BuildError]:
        """Basic fallback parser for build output to extract errors"""
        errors = []
        lines = output.splitlines()
        
        current_file = None
        current_error = []
        in_error = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Start of error block
            if "Failed to compile" in line:
                in_error = True
                continue

            if not in_error:
                continue

            # New file indicator
            if line.startswith("./") or line.startswith("../") or line.endswith(".ts") or line.endswith(".tsx"):
                if current_file and current_error:
                    errors.append(BuildError(
                        file=current_file,
                        message="\n".join(current_error),
                        type="error",
                        line=0,
                        column=0,
                        code=""
                    ))
                    current_error = []
                current_file = line.lstrip("./")
                continue

            # Error message lines
            if current_file and (line.startswith("Error:") or "Type" in line or "error" in line.lower()):
                current_error.append(line)

        # Add final error if exists
        if current_file and current_error:
            errors.append(BuildError(
                file=current_file,
                message="\n".join(current_error),
                type="error",
                line=0,
                column=0,
                code=""
            ))

        return errors

    async def _repair_code(self, errors: List[BuildError]):
        """Fix build errors using the RepairAgent"""
        try:
            # Create error report
            error_report = BuildErrorReport(errors=errors)
            
            # Use repair agent to fix errors
            success = await self.repair_agent.repair_errors(error_report)
            
            if not success:
                self.console.print("[red]Failed to repair all errors[/red]")
                
        except Exception as e:
            self.console.print(f"[red]Error during repair: {str(e)}[/red]")

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
                        2. Indexes if any
                        3. Initial seed data if needed
                        4. Do not include any RLS policies
                        
                        Format as a single SQL file with proper ordering of operations. dont include any other text no markdown, just code. Do not wrap the code in ```sql tags.""",
                    },
                    {
                        "role": "user",
                        "content": f"Generate pgsql migration for: {json.dumps(self.spec.model_dump(), indent=2)}",
                    },
                ],
                model="gpt-4o",
            )
            return migrations
        except Exception as e:
            self.console.print(f"[red]Failed to generate SQL migration: {e}[/red]")
            raise

    def initialize_project(self, project_ref: str) -> None:
        """Initialize and link Supabase project without migrations"""
        try:
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
                raise Exception(
                    "Invalid project ref format. Must be a 20-character alphanumeric string."
                )

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
                self.console.print("[green]✓ Supabase project initialized[/green]")

            # Login to Supabase (interactive)
            self.console.print("\n[yellow]Supabase Login Required[/yellow]")
            self.console.print("Press Enter to open your browser for authentication...")
            subprocess.run(
                ["npx", "supabase", "login"],
                cwd=self.project_path,
                check=True,
            )
            self.console.print("[green]✓ Successfully logged in to Supabase[/green]")

            # Link to remote project
            self.console.print(
                f"\n[yellow]Linking to Supabase project: {clean_project_ref}[/yellow]"
            )
            subprocess.run(
                [
                    "npx",
                    "supabase",
                    "link",
                    "--project-ref",
                    clean_project_ref,
                    "--password",
                    "",
                ],
                cwd=self.project_path,
                check=True,
            )
            self.console.print("[green]✓ Project linked successfully[/green]")

        except subprocess.TimeoutExpired:
            raise Exception("Operation timed out while initializing project")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise Exception(f"Project initialization failed: {error_msg}")

    def apply_migration(
        self, project_ref: str, anon_key: str, service_key: str
    ) -> None:
        """Apply migration to Supabase project"""
        try:
            if self.spec is None:
                self.console.print("[yellow]No spec provided, skipping migration generation[/yellow]")
                return

            # Generate migration SQL
            self.console.print("\n[yellow]Generating migration SQL...[/yellow]")
            migration_sql = self.get_migration_sql()

            # Create migrations directory
            migrations_dir = Path(self.project_path) / "supabase" / "migrations"
            migrations_dir.mkdir(parents=True, exist_ok=True)

            # Write migration file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            migration_file = migrations_dir / f"{timestamp}_initial_schema.sql"
            migration_file.write_text(migration_sql)

            # Push the migration
            self.console.print("\n[yellow]Pushing migration to remote database...[/yellow]")
            subprocess.run(
                ["npx", "supabase", "db", "push"],
                cwd=self.project_path,
                check=True,
            )
            self.console.print("[green]✓ Migration applied successfully[/green]")

        except subprocess.TimeoutExpired:
            raise Exception("Operation timed out while applying migration")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise Exception(f"Migration failed: {error_msg}")

    def setup_environment(
        self, project_ref: str, anon_key: str, service_key: str
    ) -> None:
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
            # Write to .env.local in the project directory
            env_file = Path(self.project_path) / ".env.local"
            env_file.write_text(env_content)
            
            self.console.print("[green]✓ Environment variables set up successfully in .env.local[/green]")

        except Exception as e:
            self.console.print(f"[red]Failed to set up environment variables: {e}[/red]")
            raise

    def _prompt_credentials(self) -> tuple[str, str, str]:
        """Prompt user for Supabase credentials if not in spec"""
        self.console.print("\n[bold yellow]Supabase Credentials Required[/bold yellow]")
        self.console.print("Please provide your Supabase project credentials:")

        project_ref = Prompt.ask(
            "\nProject Reference or URL",
            default=getattr(self.spec.supabaseConfig, "projectRef", "")
            if hasattr(self.spec, "supabaseConfig")
            else "",
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

    def setup(
        self, project_ref: str = None, anon_key: str = None, service_key: str = None
    ) -> None:
        """Complete Supabase setup including migrations and environment variables"""
        try:
            self.console.print("\n[bold]Starting Supabase Setup[/bold]")

            # If any credentials are missing, prompt for all of them
            if not all([project_ref, anon_key, service_key]):
                self.console.print("\n[bold yellow]Supabase Credentials Required[/bold yellow]")
                self.console.print("Please provide your Supabase project credentials:\n")

                project_ref = Prompt.ask(
                    "Project Reference or URL",
                    default=getattr(self.spec.supabaseConfig, "projectRef", "")
                    if hasattr(self.spec, "supabaseConfig")
                    else "",
                )

                anon_key = Prompt.ask(
                    "Anon Key (public)",
                    password=False,
                )

                service_key = Prompt.ask(
                    "Service Role Key (secret)",
                    password=True,
                )

            # First set up environment variables (non-interactive)
            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[bold]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Setting up environment variables...")
                self.setup_environment(project_ref, anon_key, service_key)
                progress.update(task, completed=True)

            # Then handle the interactive parts without progress spinner
            self.apply_migration(project_ref, anon_key, service_key)

            self.console.print("\n[green bold]✅ Supabase setup completed successfully[/green bold]")

        except Exception as e:
            self.console.print(f"\n[red bold]❌ Supabase setup failed: {str(e)}[/red bold]")
            raise
