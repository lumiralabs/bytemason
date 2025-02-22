from lumos import lumos
from blueberry.models import (
    Intent,
    ProjectSpec,
    GeneratedCode,
    FileMode,
    FileContent,
    BuildError,
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

            # # Create specs directory if it doesn't exist
            # os.makedirs("specs", exist_ok=True)

            # # Save the spec to a file
            # spec_dict = spec.model_dump()
            # spec_file = os.path.join(
            #     "specs", f"{spec.name.lower().replace(' ', '_')}_spec.json"
            # )
            # with open(spec_file, "w") as f:
            #     json.dump(spec_dict, f, indent=2)

            # self.console.print(f"[green]✓ Specification saved to: {spec_file}[/green]")

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
                {"role": "user", "content": prompt},
            ],
            response_format=GeneratedCode,
            model="gpt-4o",
        )

        # Log the raw response
        self._log_ai_response(prompt, response.model_dump(), "initial_generation")

        return response

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
                errors = self._parse_build_output(full_output)
                if errors:
                    self.console.print(f"[yellow]Build failed with {len(errors)} errors[/yellow]")
                    for error in errors:
                        self.console.print(f"[red]Error in {error.file}: {error.message}[/red]")
                return errors

            self.console.print("[green]Build completed successfully[/green]")
            return []

        except Exception as e:
            self.console.print(f"[red]Build process failed: {str(e)}[/red]")
            return []

    def _parse_build_output(self, output: str) -> List[BuildError]:
        """Parse build output to extract all errors"""
        errors = []
        current_file = "unknown"
        current_error_lines = []
        
        # Split output into lines and process
        lines = output.splitlines()
        
        # Track Next.js specific error context
        in_error_block = False
        error_block_lines = []
        current_error = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect start of Next.js error block
            if line == "Failed to compile.":
                in_error_block = True
                continue

            if in_error_block:
                # Detect file path at start of error
                if line.startswith("./"):
                    # If we were collecting a previous error, save it
                    if error_block_lines:
                        errors.append(BuildError(
                            file=current_file,
                            message="\n".join(error_block_lines),
                            type="next.js",
                            line=current_error.get("line", 0) if current_error else 0,
                            column=current_error.get("column", 0) if current_error else 0,
                            code=current_error.get("code", "") if current_error else ""
                        ))
                        error_block_lines = []
                        current_error = None
                    
                    current_file = line.strip("./")
                    continue

                # Parse Next.js specific error information
                if line.startswith("Error:"):
                    current_error = {"type": "error"}
                    error_block_lines.append(line.replace("Error:", "").strip())
                    continue
                
                # Extract line and column numbers from code frame
                if ",-[" in line:
                    match = re.search(r'\[.*:(\d+):(\d+)\]', line)
                    if match and current_error:
                        current_error["line"] = int(match.group(1))
                        current_error["column"] = int(match.group(2))
                    continue

                # Collect error message lines
                if current_error:
                    # Skip the code frame lines
                    if not any(skip in line for skip in [',-[', '| ', ':`----']):
                        error_block_lines.append(line)

            # Regular error line processing
            elif any(indicator in line.lower() for indicator in ['error', 'failed', 'exception']):
                # Try to extract file path if present
                file_match = re.search(r'[./\\]?([^/\\:]+\.[a-zA-Z]+)[:\(]?(\d+)?(?:[:\(](\d+)?)?', line)
                if file_match:
                    if current_error_lines:
                        errors.append(BuildError(
                            file=current_file,
                            message="\n".join(current_error_lines),
                            type="error",
                            line=int(file_match.group(2) or 0),
                            column=int(file_match.group(3) or 0),
                            code=""
                        ))
                        current_error_lines = []
                    
                    current_file = file_match.group(1)
                    current_error_lines = [line]
                else:
                    if current_error_lines:
                        current_error_lines.append(line)
                    else:
                        current_file = "unknown"
                        current_error_lines = [line]

        # Add any remaining error
        if error_block_lines:
            errors.append(BuildError(
                file=current_file,
                message="\n".join(error_block_lines),
                type="next.js",
                line=current_error.get("line", 0) if current_error else 0,
                column=current_error.get("column", 0) if current_error else 0,
                code=current_error.get("code", "") if current_error else ""
            ))
        elif current_error_lines:
            errors.append(BuildError(
                file=current_file,
                message="\n".join(current_error_lines),
                type="error",
                line=0,
                column=0,
                code=""
            ))

        return errors

    async def _repair_code(self, errors: List[BuildError]):
        """Fix build errors using AI with ReAct pattern"""
        # Group errors by file to handle multiple errors in same file together
        errors_by_file = {}
        for error in errors:
            if error.file != "unknown":
                if error.file not in errors_by_file:
                    errors_by_file[error.file] = []
                errors_by_file[error.file].append(error)

        for file_path, file_errors in errors_by_file.items():
            try:
                full_path = self.project_path / file_path
                if not full_path.exists():
                    continue

                # Create backup before any modifications
                backup_dir = self.project_path / ".backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{file_path}.{timestamp}.bak"
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_path)

                # Read the entire file content
                current_content = full_path.read_text()
                
                # Check if this is a Next.js Server/Client Component issue
                is_client_component_issue = any(
                    "It only works in a Client Component" in error.message 
                    for error in file_errors
                )

                if is_client_component_issue:
                    # Simplified prompt for Client Component conversion
                    prompt = f"""Fix Next.js Client Component error in this file by converting it to a Client Component.

                        File: {file_path}

                        Current content:
                        ```typescript
                        {current_content}
                        ```

                        Requirements:
                        1. Add 'use client' directive at the very top of the file
                        2. Keep all existing imports and functionality
                        3. Ensure proper TypeScript types
                        4. Return valid JSX/TSX
                        5. Format the code properly

                        Provide ONLY the complete fixed code without any explanations or markdown formatting."""
                else:
                    # Format errors for standard prompt
                    error_descriptions = "\n".join([
                        f"Error {i+1}:\n"
                        f"  Type: {error.type}\n"
                        f"  Message: {error.message}\n"
                        f"  Line: {error.line}\n"
                        f"  Column: {error.column}\n"
                        f"  Code: {error.code}"
                        for i, error in enumerate(file_errors)
                    ])

                    prompt = f"""You are an expert Next.js and TypeScript developer. Fix the following errors in this file using careful reasoning.

                        File: {file_path}
                        Number of errors: {len(file_errors)}

                        Errors to fix:
                        {error_descriptions}

                        Current file content:
                        ```typescript
                        {current_content}
                        ```

                        Follow this exact format in your response:
                        1. ANALYSIS
                        Analyze each error and explain what's wrong. List any dependencies or imports that might be missing.

                        2. SOLUTION PLAN
                        Outline the steps needed to fix all errors. Consider how fixes might interact with each other.

                        3. IMPLEMENTATION
                        Provide the complete fixed file content. Include ALL necessary imports and dependencies.

                        4. VERIFICATION STEPS
                        List specific things to check to ensure the fix worked.

                        Begin your response with "ANALYSIS:" and clearly separate each section."""

                # Try repair with up to 3 attempts
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        response = await lumos.call_ai_async(
                            messages=[
                                {
                                    "role": "system",
                                    "content": """You are an expert Next.js TypeScript developer specializing in fixing build errors.
                                    For Client Component issues:
                                    - Always start with 'use client' directive
                                    - Ensure proper TypeScript types
                                    - Return valid JSX/TSX
                                    - Format code properly with consistent indentation"""
                                },
                                {"role": "user", "content": prompt}
                            ],
                            model="gpt-4o",
                        )

                        if is_client_component_issue:
                            # For Client Component issues, clean and validate the response
                            implementation = response.strip()
                            
                            # Remove any markdown code blocks
                            implementation = re.sub(r'^```[\w]*\n|```$', '', implementation, flags=re.MULTILINE).strip()
                            
                            # Ensure 'use client' directive is properly formatted
                            if not implementation.startswith('"use client"') and not implementation.startswith("'use client'"):
                                implementation = '"use client";\n\n' + implementation
                            
                            # Basic syntax validation
                            try:
                                import ast
                                ast.parse(implementation)
                            except SyntaxError as e:
                                self.console.print(f"[yellow]Syntax error in generated code: {str(e)}[/yellow]")
                                continue
                        else:
                            # Parse sections from response for non-client-component issues
                            sections = {}
                            current_section = None
                            current_content = []
                            
                            for line in response.split('\n'):
                                if line.strip().upper() in ['ANALYSIS:', 'SOLUTION PLAN:', 'IMPLEMENTATION:', 'VERIFICATION STEPS:']:
                                    if current_section:
                                        sections[current_section] = '\n'.join(current_content).strip()
                                    current_section = line.strip().upper().replace(':', '')
                                    current_content = []
                                else:
                                    current_content.append(line)
                            
                            if current_section:
                                sections[current_section] = '\n'.join(current_content).strip()

                            # Log the repair attempt
                            self._log_ai_response(
                                prompt,
                                {
                                    "attempt": attempt + 1,
                                    "analysis": sections.get('ANALYSIS', ''),
                                    "solution_plan": sections.get('SOLUTION PLAN', ''),
                                    "verification": sections.get('VERIFICATION STEPS', '')
                                },
                                "repair_attempt"
                            )

                            implementation = sections.get('IMPLEMENTATION', '').strip()
                            implementation = re.sub(r'^```[\w]*\n|```$', '', implementation, flags=re.MULTILINE).strip()

                        if not implementation:
                            raise ValueError("No implementation provided in AI response")

                        # Apply the fix
                        full_path.write_text(implementation)
                        self.console.print(f"[green]Applied fix attempt {attempt + 1} for {file_path}[/green]")

                        # Verify the fix worked
                        test_errors = await self._run_build()
                        remaining_errors = [e for e in test_errors if e.file == file_path]
                        
                        if not remaining_errors:
                            self.console.print(f"[green]Successfully fixed all errors in {file_path}[/green]")
                            break
                        else:
                            self.console.print(f"[yellow]Fix attempt {attempt + 1} didn't resolve all errors, trying again...[/yellow]")
                            if attempt == max_attempts - 1:
                                # Restore from backup on final failed attempt
                                shutil.copy2(backup_path, full_path)
                                self.console.print(f"[red]Failed to fix {file_path} after {max_attempts} attempts. Restored backup.[/red]")

                    except Exception as e:
                        self.console.print(f"[red]Error in fix attempt {attempt + 1} for {file_path}: {str(e)}[/red]")
                        if attempt == max_attempts - 1:
                            # Restore from backup
                            shutil.copy2(backup_path, full_path)
                            self.console.print(f"[red]Failed to fix {file_path}. Restored backup.[/red]")

            except Exception as e:
                self.console.print(f"[red]Failed to process {file_path}: {str(e)}[/red]")
                # Restore from backup if it exists
                if 'backup_path' in locals() and backup_path.exists():
                    shutil.copy2(backup_path, full_path)
                    self.console.print(f"[yellow]Restored backup for {file_path}[/yellow]")

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
