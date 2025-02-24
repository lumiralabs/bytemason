from pathlib import Path
import shutil
from datetime import datetime
from rich.console import Console
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
            "generate_fix": self._generate_fix,
            "analyze_dependencies": self._analyze_dependencies  # Add new tool
        }

    async def _analyze_build_errors_with_ai(self, build_output: str) -> BuildErrorReport:
        """Use AI to analyze build errors more intelligently"""
        try:
            prompt = f"""Analyze this Typescript Next.js 14 app router build output and extract all errors.
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
                    {"role": "system", "content": "You are an expert at analyzing Next.js 14 app router and TypeScript build errors."},
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
            for error in error_report.errors:
                if error.file != "unknown":
                    await self._repair_single_error(error)
            return True
        except Exception as e:
            self.console.print(f"[red]Error during repair: {str(e)}[/red]")
            return False

    async def _repair_single_error(self, error: BuildError, max_turns: int = 5) -> None:
        """Handle a single error using the agent loop."""
        system_prompt = """You are an expert Next.js 14 app router and TypeScript developer specializing in fixing build errors.
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

        analyze_dependencies:
        - Input: JSON string with file path and import statement
        Example: {"tool": "analyze_dependencies", "input": "{\\"file\\": \\"path/to/file.ts\\", \\"import\\": \\"import { Something } from './other'\\"}", "thought": "Checking import dependencies"}

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
        
        while turn < max_turns:
            turn += 1
            
            # Get next action from AI
            messages.append({"role": "user", "content": next_prompt})
            response = await lumos.call_ai_async(
                messages=messages,
                model="gpt-4o",
                response_format=AgentResponse
            )
            self.console.print(f"\n[dim]{response.model_dump_json(indent=2)}[/dim]")
            messages.append({"role": "assistant", "content": response.model_dump_json()})
            
            # Check for completion
            if response.status == "fixed":
                # Verify fix by running build error analysis
                if await self._verify_fix(error.file):
                    self.console.print(f"[green]Successfully fixed error in {error.file}: {response.explanation}[/green]")
                    return
                else:
                    # If verification failed, continue trying
                    next_prompt = "The fix did not resolve the error. Please try another approach."
                    continue
            elif response.status == "failed":
                self.console.print(f"[red]Failed to fix error in {error.file}: {response.explanation}[/red]")
                return
                
            # Execute action if present
            if response.action:
                observation = await self._execute_action(response.action)
                next_prompt = f"Observation: {observation}"
            else:
                next_prompt = "No action specified. Please provide an action or mark as fixed/failed."

    async def _verify_fix(self, file_path: str) -> bool:
        """Verify if a fix resolved the error by analyzing build output"""
        try:
            # Run build and analyze errors
            build_output = await self._run_build()
            error_report = await self._analyze_build_errors_with_ai(build_output)
            
            # Check if the file still has errors
            return not any(error.file == file_path for error in error_report.errors)
        except Exception as e:
            self.console.print(f"[yellow]Error verifying fix: {str(e)}[/yellow]")
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
            
            result = await self.tools[action.tool](input_data)
            return result.model_dump_json() if hasattr(result, 'model_dump_json') else str(result)
        except Exception as e:
            return f"Error executing {action.tool}: {str(e)}"
            
    async def _read_file(self, file_path: str) -> FileOperation:
        """Read the current content of a file."""
        try:
            full_path = self.project_path / file_path
            content = full_path.read_text()
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
                    {"role": "system", "content": "You are a senior expert Next.js 14 app router and TypeScript developer who first identifies the root cause of the error and then plans out a fix and then implement it with all the edge cases in mind. Provide only the fixed code with no explanation."},
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

    async def _analyze_dependencies(self, data: Dict[str, str]) -> FileOperation:
        """Analyze import dependencies and suggest fixes or file creation."""
        try:
            file_path = Path(data["file"])
            import_stmt = data["import"]
            
            # Extract the import path
            import_path_match = re.search(r'from [\'"](.+?)[\'"]', import_stmt)
            if not import_path_match:
                return FileOperation(
                    success=False,
                    message="Could not parse import statement",
                    path=str(file_path)
                )
                
            import_path = import_path_match.group(1)
            
            # Resolve the full path of the imported file
            current_dir = (self.project_path / file_path).parent
            if import_path.startswith('.'):
                # Relative import
                target_path = (current_dir / import_path).resolve()
            else:
                # Non-relative import (node_modules or absolute)
                target_path = self.project_path / import_path
                
            # Add common extensions if no extension specified
            if not target_path.suffix:
                possible_extensions = ['.ts', '.tsx', '.js', '.jsx']
                for ext in possible_extensions:
                    if target_path.with_suffix(ext).exists():
                        target_path = target_path.with_suffix(ext)
                        break
                    elif (target_path / 'index').with_suffix(ext).exists():
                        target_path = (target_path / 'index').with_suffix(ext)
                        break
                        
            # Check if file exists
            if not target_path.exists():
                # Generate suggestion for missing file
                prompt = f"""Create a new TypeScript file for this import:
                Import statement: {import_stmt}
                File path: {target_path}
                
                Provide only the content for the new file, including proper exports.
                """
                
                response = await lumos.call_ai_async(
                    messages=[
                        {"role": "system", "content": "You are an expert TypeScript developer. Generate only the file content."},
                        {"role": "user", "content": prompt}
                    ],
                    model="gpt-4o"
                )
                
                return FileOperation(
                    success=True,
                    message="Generated content for missing file",
                    path=str(target_path.relative_to(self.project_path)),
                    content=response.strip(),
                    suggested_action="create_file"
                )
            
            # If file exists, analyze its exports
            file_content = target_path.read_text()
            
            # Extract what's being imported
            import_items = re.findall(r'{(.+?)}', import_stmt)
            imported_names = [name.strip() for items in import_items for name in items.split(',')]
            
            # Check if the imported items exist in the target file
            missing_exports = []
            for name in imported_names:
                if not re.search(rf'export.+?{name}\b', file_content):
                    missing_exports.append(name)
            
            if missing_exports:
                return FileOperation(
                    success=True,
                    message=f"Missing exports in target file: {', '.join(missing_exports)}",
                    path=str(target_path.relative_to(self.project_path)),
                    content=file_content,
                    suggested_action="add_exports"
                )
            
            return FileOperation(
                success=True,
                message="All dependencies verified",
                path=str(target_path.relative_to(self.project_path))
            )
            
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error analyzing dependencies: {str(e)}",
                path=data["file"]
            )