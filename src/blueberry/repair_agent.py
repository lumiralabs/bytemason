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
    FileOperation,
    DirectoryListing
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
        
        # Create logs directory
        log_dir = Path(project_path) / "logs"
        log_dir.mkdir(exist_ok=True)
        self.ai_log_file = log_dir / f"repair_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Available tools for the agent
        self.tools = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            # "create_backup": self._create_backup,
            # "restore_backup": self._restore_backup,
            "generate_fix": self._generate_fix,
            "analyze_dependencies": self._analyze_dependencies,  # Add new tool
            "list_directory": self._list_directory
        }

    def _log_ai_response(self, prompt: str, response: any, type: str = "repair"):
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
                model="anthropic/claude-3-5-sonnet-20241022",
                response_format=BuildErrorReport
            )
            
            # Log AI prompt and response
            self._log_ai_response(prompt, response.model_dump(), "build_error_analysis")

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
        system_prompt = """You are an advanced AI repair agent, an expert Next.js 14 App Router and TypeScript developer, dedicated to fixing build errors with maximum reasoning and precision.

        Your identity and capabilities:
        - You excel at diagnosing and correcting complex Next.js 14 (App Router) and TypeScript issues.
        - You plan, reason, and perform multi-step fixes in a methodical, iterative manner.
        - You reflect on prior steps and refine your approach as needed.

        Your process is **iterative**:
        1. **Think carefully** about what needs to be done.
        2. **Take an Action** by calling one of your available tools.
        3. **Pause** and observe the result (the “observation”).
        4. **Reflect** on whether to continue refining or finalize the fix.
        5. Repeat until the error is completely fixed or you determine it cannot be fixed.

        **Important additional rule**: 
        - If the code references a component or file (e.g., `@/components/ui/checkbox`) and that file does not exist, **create** it using the appropriate tool (`write_file` or `generate_fix`). Provide at least minimal or placeholder code that ensures the build can proceed (for example, a basic React component that exports the required functionality).

        At **any point**, you can self-reflect to confirm if the build error is fully addressed:
        - If the issue is resolved, set `"status": "fixed"` and provide a concise `"explanation"`.
        - If you cannot fix the error, set `"status": "failed"` and briefly explain why in `"explanation"`.

        You have the following **tools** (no backup actions are available):

        1. **read_file**  
        - Input: A simple string containing the file path.  
        - Example:
            ```json
            {
            "tool": "read_file",
            "input": "path/to/file.ts",
            "thought": "Need to inspect the current file content"
            }
            ```

        2. **write_file**  
        - Input: A JSON string containing `"path"` and `"content"`.  
        - Example:
            ```json
            {
            "tool": "write_file",
            "input": "{\"path\": \"path/to/file.ts\", \"content\": \"updated file content\"}",
            "thought": "Overwriting the file with the new content"
            }
            ```

        3. **generate_fix**  
        - Input: A JSON string containing `"file"`, `"current_content"`, and `"error"`.  
        - Example:
            ```json
            {
            "tool": "generate_fix",
            "input": "{\"file\": \"path/to/file.ts\", \"current_content\": \"...\", \"error\": \"...\"}",
            "thought": "Generate a code fix based on the current content and the error details"
            }
            ```

        4. **analyze_dependencies**  
        - Input: A JSON string with `"file"` and `"import"`.  
        - Example:
            ```json
            {
            "tool": "analyze_dependencies",
            "input": "{\"file\": \"path/to/file.ts\", \"import\": \"import { Something } from './other'\"}",
            "thought": "Check if the import path is valid and look for the correct file"
            }
            ```

        5. **list_directory**  
        - Input: A simple string specifying a directory path to inspect.  
        - Example:
            ```json
            {
            "tool": "list_directory",
            "input": "app/components",
            "thought": "Explore the directory structure for relevant files"
            }
            ```

        When you respond, **always** produce valid JSON matching the structure:

        ```json
        {
        "thought": "Use <thoughts> to hold reasoning. Example: <thoughts>I need to read file.ts</thoughts>",
        "action": {
            "tool": "one_of_the_tools",
            "input": "...",
            "thought": "Why you chose this tool"
        },
        "status": "thinking | fixed | failed",
        "explanation": "Explanation only if status is fixed or failed"
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
                model="anthropic/claude-3-5-sonnet-20241022",
                response_format=AgentResponse
            )
            
            # Log AI prompt and response
            self._log_ai_response(next_prompt, response.model_dump(), f"repair_turn_{turn}")
            
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

            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, "prompts", "core_prompt.md")

            with open(prompt_path, "r") as f:
                core_prompt = f.read()


            prompt = f"""Fix this file:
            
            File: {data['file']}
            Error: {data['error']}
            
            Current content:
            {core_prompt}
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
                model="anthropic/claude-3-5-sonnet-20241022"
            )
            
            # Log AI prompt and response
            self._log_ai_response(prompt, response, "generate_fix")
            
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
                        
            # Before checking if file exists, list the directory to find similar files
            dir_path = target_path.parent
            dir_listing = await self._list_directory(str(dir_path.relative_to(self.project_path)))
            
            if not target_path.exists():
                # Check for case-insensitive matches
                target_name = target_path.name.lower()
                similar_files = [
                    f for f in dir_listing.files 
                    if Path(f).name.lower() == target_name
                ]
                
                if similar_files:
                    return FileOperation(
                        success=True,
                        message=f"Found similar file with different case: {similar_files[0]}",
                        path=similar_files[0],
                        suggested_action="update_import"
                    )
                    
                # Continue with existing missing file handling...
                
            # Rest of existing _analyze_dependencies code...
            
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error analyzing dependencies: {str(e)}",
                path=data["file"]
            )

    async def _list_directory(self, dir_path: str, recursive: bool = True) -> DirectoryListing:
        """List contents of a directory, including subdirectories if recursive=True."""
        try:
            full_path = self.project_path / dir_path
            
            if not full_path.exists():
                return DirectoryListing(
                    path=dir_path,
                    exists=False,
                    is_empty=True,
                    files=[],
                    directories=[],
                    error="Directory does not exist"
                )
            
            if not full_path.is_dir():
                return DirectoryListing(
                    path=dir_path,
                    exists=True,
                    is_empty=True,
                    files=[],
                    directories=[],
                    error="Path exists but is not a directory"
                )

            try:
                files = []
                directories = []
                
                # Use rglob for recursive or glob for non-recursive
                pattern = "*" if recursive else "*"
                glob_method = full_path.rglob if recursive else full_path.glob
                
                for entry in glob_method(pattern):
                    try:
                        # Skip .git, node_modules, and .next directories
                        if any(part in ['.git', 'node_modules', '.next'] for part in entry.parts):
                            continue
                            
                        relative_path = str(entry.relative_to(self.project_path))
                        if entry.is_file():
                            files.append(relative_path)
                        elif entry.is_dir():
                            directories.append(relative_path)
                    except Exception:
                        continue

                files.sort()
                directories.sort()

                return DirectoryListing(
                    path=dir_path,
                    exists=True,
                    is_empty=len(files) == 0 and len(directories) == 0,
                    files=files,
                    directories=directories,
                    error=""
                )

            except PermissionError:
                return DirectoryListing(
                    path=dir_path,
                    exists=True,
                    is_empty=True,
                    files=[],
                    directories=[],
                    error="Permission denied when accessing directory"
                )

        except Exception as e:
            return DirectoryListing(
                path=dir_path,
                exists=False,
                is_empty=True,
                files=[],
                directories=[],
                error=f"Error listing directory: {str(e)}"
            )