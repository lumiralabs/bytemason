from pathlib import Path
import shutil
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from lumos import lumos
from typing import List, Dict, Any, Optional
from blueberry.models import (
    BuildError,
    BuildErrorReport,
    AgentAction,
    AgentResponse,
    FileOperation
)
import re
import json
import asyncio
import os

class RepairAgent:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.console = Console()
        self.backup_dir = self.project_path / ".backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Available tools for the agent
        self.tools = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "create_backup": self._create_backup,
            "restore_backup": self._restore_backup,
            "generate_fix": self._generate_fix
        }
        
        # Initialize progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )

    def _create_error_table(self, error: BuildError) -> Table:
        """Create a rich table to display error information"""
        table = Table(show_header=True, header_style="bold magenta", border_style="blue")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("File", error.file)
        table.add_row("Type", error.type)
        table.add_row("Message", error.message)
        if error.line:
            table.add_row("Line", str(error.line))
        if error.column:
            table.add_row("Column", str(error.column))
        if error.code:
            table.add_row("Code", error.code)
            
        return table

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

            return response

        except Exception as e:
            self.console.print(f"[yellow]AI error analysis failed: {str(e)}[/yellow]")
            return BuildErrorReport(errors=[])

    async def _run_build(self) -> str:
        """Run the build and return its output"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npm",
                "run",
                "build",
                "--no-color",
                cwd=str(self.project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"}
            )
            stdout, stderr = await process.communicate()
            return stdout.decode() + "\n" + stderr.decode()
        except Exception as e:
            return str(e)

    async def repair_errors(self, error_report: BuildErrorReport) -> bool:
        """Main entry point for repairing code based on build errors."""
        try:
            total_errors = len([e for e in error_report.errors if e.file != "unknown"])
            
            if total_errors == 0:
                self.console.print("[green]No errors to fix![/green]")
                return True
                
            self.console.print(Panel(
                f"[bold blue]Starting repair process for {total_errors} error(s)[/bold blue]",
                border_style="blue"
            ))
            
            for error in error_report.errors:
                if error.file != "unknown":
                    self.console.print("\n" + "="*80)
                    self.console.print(self._create_error_table(error))
                    await self._repair_single_error(error)
                    
            return True
        except Exception as e:
            self.console.print(Panel(
                f"[bold red]Error during repair:[/bold red]\n{str(e)}",
                border_style="red"
            ))
            return False

    async def _repair_single_error(self, error: BuildError, max_turns: int = 5) -> None:
        """Handle a single error using the agent loop."""
        system_prompt = """You are an expert Next.js and TypeScript developer specializing in fixing build errors.
        You run in a loop of Thought, Action, PAUSE, Observation.
        At each step, you:
        1. Think about what needs to be done
        2. Take an Action from your available tools
        3. PAUSE to receive the Observation from that action
        4. Continue until you've fixed the error or determined it cannot be fixed
        
        Your available actions are:
        
        read_file:
        - Input: Simple string with file path
        Example: {"tool": "read_file", "input": "path/to/file.ts", "thought": "Need to read the file content"}
        
        write_file:
        - Input: JSON string with path and content
        Example: {"tool": "write_file", "input": "{\\"path\\": \\"path/to/file.ts\\", \\"content\\": \\"file content here\\"}", "thought": "Writing fixed content"}
        
        create_backup:
        - Input: Simple string with file path
        Example: {"tool": "create_backup", "input": "path/to/file.ts", "thought": "Creating backup before changes"}
        
        restore_backup:
        - Input: Simple string with file path
        Example: {"tool": "restore_backup", "input": "path/to/file.ts", "thought": "Restoring previous backup"}
        
        generate_fix:
        - Input: JSON string with file, current_content, and error
        Example: {"tool": "generate_fix", "input": "{\\"file\\": \\"path/to/file.ts\\", \\"current_content\\": \\"..\\", \\"error\\": \\"...\\"}", "thought": "Generating fix for the error"}

        Always create a backup before modifying any file.
        Think carefully about each step and explain your reasoning.
        
        Respond in a structured format with:
        {
          "thought": "Your current thoughts about what needs to be done",
          "action": {
            "tool": "tool_name",
            "input": "tool input as described above",
            "thought": "why you're taking this action"
          },
          "status": "thinking|fixed|failed",
          "explanation": "only needed if status is fixed or failed"
        }
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        initial_prompt = f"""
        Error to fix:
        File: {error.file}
        Type: {error.type}
        Message: {error.message}
        Line: {error.line}
        Column: {error.column}
        Code: {error.code}
        
        Fix this error using the available actions.
        """
        
        turn = 0
        next_prompt = initial_prompt
        
        with self.progress:
            task = self.progress.add_task(f"[cyan]Repairing {error.file}...", total=max_turns)
            
            while turn < max_turns:
                turn += 1
                self.progress.update(task, advance=1, description=f"[cyan]Repair attempt {turn}/{max_turns}")
                
                # Get next action from AI
                messages.append({"role": "user", "content": next_prompt})
                response = await lumos.call_ai_async(
                    messages=messages,
                    model="gpt-4o",
                    response_format=AgentResponse
                )
                
                # Display thought process in a panel
                if response.thought:
                    self.console.print(Panel(
                        f"[bold blue]Thinking:[/bold blue]\n{response.thought}",
                        border_style="blue"
                    ))
                
                messages.append({"role": "assistant", "content": response.model_dump_json()})
                
                # Check for completion
                if response.status == "fixed":
                    # Verify fix
                    self.progress.update(task, description="[yellow]Verifying fix...")
                    if await self._verify_fix(error.file):
                        self.progress.update(task, description="[green]Fix verified!")
                        self.console.print(Panel(
                            f"[bold green]Successfully fixed error in {error.file}:[/bold green]\n{response.explanation}",
                            border_style="green"
                        ))
                        return
                    else:
                        self.progress.update(task, description="[red]Fix verification failed")
                        next_prompt = "The fix did not resolve the error. Please try another approach."
                        continue
                elif response.status == "failed":
                    self.progress.update(task, description="[red]Repair failed")
                    self.console.print(Panel(
                        f"[bold red]Failed to fix error in {error.file}:[/bold red]\n{response.explanation}",
                        border_style="red"
                    ))
                    return
                
                # Execute action if present
                if response.action:
                    self.progress.update(task, description=f"[cyan]Executing {response.action.tool}...")
                    observation = await self._execute_action(response.action)
                    next_prompt = f"Observation: {observation}"
                else:
                    next_prompt = "No action specified. Please provide an action or mark as fixed/failed."

    async def _verify_fix(self, file_path: str) -> bool:
        """Verify if a fix resolved the error by analyzing build output"""
        try:
            # Run build and analyze errors
            with self.progress:
                build_task = self.progress.add_task("[yellow]Running build...", total=1)
                build_output = await self._run_build()
                self.progress.update(build_task, advance=1)
                
                analyze_task = self.progress.add_task("[yellow]Analyzing build output...", total=1)
                error_report = await self._analyze_build_errors_with_ai(build_output)
                self.progress.update(analyze_task, advance=1)
            
            # Check if the file still has errors
            has_errors = any(error.file == file_path for error in error_report.errors)
            if has_errors:
                self.console.print(Panel(
                    "[yellow]Verification failed - errors still present[/yellow]",
                    border_style="yellow"
                ))
            return not has_errors
        except Exception as e:
            self.console.print(Panel(
                f"[bold red]Error during verification:[/bold red]\n{str(e)}",
                border_style="red"
            ))
            return False

    async def _execute_action(self, action: AgentAction) -> str:
        """Execute an agent action and return the observation"""
        if action.tool not in self.tools:
            return f"Unknown action: {action.tool}"
        
        try:
            # Parse input as JSON if it's a JSON string
            input_data = action.input
            if action.tool in ["write_file", "generate_fix"]:
                try:
                    input_data = json.loads(action.input)
                except json.JSONDecodeError:
                    return f"Error: Input for {action.tool} must be valid JSON"
            
            # Execute the action with progress indicator
            with self.progress:
                task = self.progress.add_task(
                    f"[cyan]Executing {action.tool}...",
                    total=1
                )
                result = await self.tools[action.tool](input_data)
                self.progress.update(task, advance=1)
            
            # Display the result in a nice format
            if hasattr(result, 'model_dump_json'):
                result_dict = json.loads(result.model_dump_json())
                if result_dict.get('success', False):
                    self.console.print(Panel(
                        f"[green]{result_dict.get('message', 'Operation successful')}[/green]",
                        border_style="green"
                    ))
                else:
                    self.console.print(Panel(
                        f"[red]{result_dict.get('message', 'Operation failed')}[/red]",
                        border_style="red"
                    ))
                return result.model_dump_json()
            return str(result)
        except Exception as e:
            error_msg = f"Error executing {action.tool}: {str(e)}"
            self.console.print(Panel(error_msg, border_style="red"))
            return error_msg
            
    async def _read_file(self, file_path: str) -> FileOperation:
        """Read the current content of a file."""
        try:
            full_path = self.project_path / file_path
            content = full_path.read_text()
            
            # Display file content in a syntax-highlighted panel
            if content.strip():
                self.console.print(Panel(
                    Syntax(
                        content,
                        "python" if file_path.endswith('.py') else "typescript",
                        theme="monokai",
                        line_numbers=True
                    ),
                    title=f"[bold blue]{file_path}[/bold blue]",
                    border_style="blue"
                ))
            
            return FileOperation(
                success=True,
                message="File read successfully",
                path=file_path,
                content=content
            )
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error reading file: {str(e)}",
                path=file_path
            )
            
    async def _write_file(self, data: Dict[str, str]) -> FileOperation:
        """Write content to a file."""
        try:
            full_path = self.project_path / data["path"]
            full_path.write_text(data["content"])
            return FileOperation(
                success=True,
                message="File written successfully",
                path=data["path"]
            )
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error writing file: {str(e)}",
                path=data["path"]
            )
            
    async def _create_backup(self, file_path: str) -> FileOperation:
        """Create a backup of a file."""
        try:
            full_path = self.project_path / file_path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{file_path}.{timestamp}.bak"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(full_path, backup_path)
            return FileOperation(
                success=True,
                message=f"Created backup at {backup_path}",
                path=str(backup_path)
            )
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error creating backup: {str(e)}",
                path=file_path
            )
            
    async def _restore_backup(self, file_path: str) -> FileOperation:
        """Restore the most recent backup of a file."""
        try:
            # Find most recent backup
            backups = list(self.backup_dir.glob(f"{file_path}.*.bak"))
            if not backups:
                return FileOperation(
                    success=False,
                    message="No backup found",
                    path=file_path
                )
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            
            # Restore it
            full_path = self.project_path / file_path
            shutil.copy2(latest_backup, full_path)
            return FileOperation(
                success=True,
                message=f"Restored backup from {latest_backup}",
                path=file_path
            )
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error restoring backup: {str(e)}",
                path=file_path
            )
            
    async def _generate_fix(self, data: Dict[str, str]) -> FileOperation:
        """Generate a fix for the file."""
        try:
            prompt = f"""Fix this file:
            
            File: {data['file']}
            Error: {data['error']}
            
            Current content:
            ```typescript
            {data['current_content']}
            ```
            
            Provide only the fixed code with no explanation:
            """
            
            response = await lumos.call_ai_async(
                messages=[
                    {"role": "system", "content": "You are an expert Next.js TypeScript developer. Provide only the fixed code with no explanation."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4o"
            )
            
            # Clean up the response
            code = response.replace("```typescript", "").replace("```", "").strip()
            
            return FileOperation(
                success=True,
                message="Generated fix successfully",
                path=data['file'],
                content=code
            )
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error generating fix: {str(e)}",
                path=data['file']
            )