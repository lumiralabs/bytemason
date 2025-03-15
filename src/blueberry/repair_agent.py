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
from dotenv import load_dotenv

# Loading the custom env vars
load_dotenv()

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
                # model="anthropic/claude-3-5-sonnet-20241022",
                model = os.getenv("REPAIR_AGENT_MODEL"),
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
        system_prompt = """
        <agent_identity>
        You are CodeFixer, an expert Next.js 14 App Router and TypeScript repair agent. You methodically diagnose and fix build errors with surgical precision and deep reasoning.
        </agent_identity>
        <agent_expertise>

        Advanced understanding of Next.js 14 App Router architecture and conventions
        TypeScript type system mastery including generics, interfaces, and module resolution
        Modern React patterns and best practices
        JavaScript/TypeScript build systems and dependency management

        </agent_expertise>
        <repair_process>
        Follow this structured approach to fixing errors:

        Analyze: Carefully examine the error details and affected code
        Plan: Outline a specific strategy to address the root cause
        Execute: Use your tools to implement the solution
        Verify: Confirm the fix addresses the original error without introducing new issues
        Reflect: Consider if further improvements are needed

        </repair_process>
        <critical_guidelines>

        Create missing components or files when imports reference non-existent paths
        Provide minimal working implementations that satisfy type requirements
        Maintain consistent coding style with the existing project
        Fix one error completely before moving to the next
        If multiple solutions exist, choose the most robust and maintainable approach
        Be thorough but pragmatic - aim for working code over perfection

        </critical_guidelines>
        <tools>
        read_file

        Purpose: Retrieve current file content for inspection
        Input: Simple string with file path
        Example:

        jsonCopy{
        "tool": "read_file",
        "input": "components/Button.tsx",
        "thought": "Need to examine the current Button component implementation"
        }
        write_file

        Purpose: Save modified or new file content
        Input: JSON object with path and content properties
        Example:

        jsonCopy{
        "tool": "write_file",
        "input": {
            "path": "components/Button.tsx",
            "content": "// Updated file content here"
        },
        "thought": "Implementing fixed Button component with proper type definitions"
        }
        generate_fix

        Purpose: Create an optimal solution for the specific error
        Input: JSON object with file path, current content, and error details
        Example:

        jsonCopy{
        "tool": "generate_fix",
        "input": {
            "file": "components/Button.tsx",
            "current_content": "// Current problematic code",
            "error": "Type '{ children: string; }' is not assignable to type 'IntrinsicAttributes'"
        },
        "thought": "The Button component needs proper typing for its props"
        }
        analyze_dependencies

        Purpose: Trace import relationships and validate dependencies
        Input: JSON object with file path and import statement
        Example:

        jsonCopy{
        "tool": "analyze_dependencies",
        "input": {
            "file": "pages/index.tsx",
            "import": "import { Button } from '@/components/ui/button'"
        },
        "thought": "Checking if the Button component exists at the specified import path"
        }
        list_directory

        Purpose: Explore project structure to locate relevant files
        Input: Simple string with directory path
        Example:

        jsonCopy{
        "tool": "list_directory",
        "input": "components",
        "thought": "Looking for existing UI components that might be referenced"
        }
        </tools>
        <special_cases>

        When encountering imports from '@/components/ui/*', check if shadcn/ui is being used and create appropriate components
        For TypeScript path alias errors (@/*), ensure tsconfig.json has proper path mappings
        For React hook usage errors, verify component naming and context follows React rules
        For Server/Client component conflicts, add proper "use client" directives

        </special_cases>
        <response_format>
        Always structure your responses as valid JSON with these fields:
        jsonCopy{
        "thought": "<detailed_reasoning>Your step-by-step analysis of the problem and solution approach</detailed_reasoning>",
        "action": {
            "tool": "one_of_the_available_tools",
            "input": "appropriate_input_for_the_chosen_tool",
            "thought": "Brief explanation of why you selected this specific action"
        },
        "status": "thinking | fixed | failed",
        "explanation": "Only provide when status is 'fixed' or 'failed', explaining the resolution or why the error couldn't be fixed"
        }
        </response_format>

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
                # model="anthropic/claude-3-5-sonnet-20241022",
                  model = os.getenv("REPAIR_AGENT_MODEL"),
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
                # model="anthropic/claude-3-5-sonnet-20241022"
                  model = os.getenv("REPAIR_AGENT_MODEL"),
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
            
            # Extract the imported symbols
            imported_symbols = []
            symbols_match = re.search(r'import\s+{([^}]+)}', import_stmt)
            if symbols_match:
                imported_symbols = [s.strip() for s in symbols_match.group(1).split(',')]
            elif "import " in import_stmt and " from " in import_stmt:
                default_import = re.search(r'import\s+([^{]\S+)', import_stmt)
                if default_import:
                    imported_symbols = [default_import.group(1).strip()]
            
            # Resolve the full path of the imported file
            current_dir = (self.project_path / file_path).parent
            
            # Handle different import types
            if import_path.startswith('.'):
                # Relative import
                target_path = (current_dir / import_path).resolve()
            elif import_path.startswith('@/'):
                # Path alias starting with @/ - typically maps to project root
                alias_path = import_path[2:]  # Remove '@/'
                target_path = self.project_path / alias_path
                
                # # If src/ doesn't exist, try from project root
                # if not (self.project_path / 'src').exists():
                #     target_path = self.project_path / alias_path
            else:
                # Non-relative import (node_modules or absolute)
                target_path = self.project_path / import_path
                
            # Track if we need file extension resolution
            needs_extension = not target_path.suffix
            needs_index = False
                
            # Add common extensions if no extension specified
            if needs_extension:
                possible_extensions = ['.ts', '.tsx', '.js', '.jsx']
                for ext in possible_extensions:
                    if target_path.with_suffix(ext).exists():
                        target_path = target_path.with_suffix(ext)
                        needs_extension = False
                        break
                    elif (target_path / 'index').with_suffix(ext).exists():
                        target_path = (target_path / 'index').with_suffix(ext)
                        needs_extension = False
                        needs_index = True
                        break
            
            # Before checking if file exists, list the directory to find similar files
            try:
                dir_path = target_path.parent
                if not needs_extension:
                    dir_listing = await self._list_directory(str(dir_path.relative_to(self.project_path)))
                else:
                    # If still resolving extension, use what we have
                    dir_listing = await self._list_directory(str(dir_path.relative_to(self.project_path)))
            except Exception:
                dir_listing = DirectoryListing(
                    path=str(dir_path),
                    exists=False,
                    is_empty=True,
                    files=[],
                    directories=[],
                    error="Error listing directory"
                )
                
            # Check if the file exists
            if target_path.exists():
                # File exists, return its content
                try:
                    content = target_path.read_text()
                    return FileOperation(
                        success=True,
                        message=f"Found existing file at {target_path.relative_to(self.project_path)}",
                        path=str(target_path.relative_to(self.project_path)),
                        content=content
                    )
                except Exception as e:
                    return FileOperation(
                        success=False,
                        message=f"File exists but couldn't be read: {str(e)}",
                        path=str(target_path.relative_to(self.project_path))
                    )
            else:
                # File doesn't exist, look for similar files or suggest creation
                
                # Check for case-insensitive matches
                if dir_listing.files:
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
                
                # Try to determine best extension for file creation
                if needs_extension:
                    # First try to match the importing file's extension
                    if file_path.suffix in ['.tsx', '.jsx']:
                        suggested_extension = '.tsx' if '.ts' in file_path.suffix else '.jsx'
                    else:
                        suggested_extension = '.ts' if '.ts' in file_path.suffix else '.js'
                    
                    # Add index/ suffix if it seems to be a directory
                    if needs_index or (dir_listing.exists and dir_listing.is_empty):
                        proposed_path = str((target_path / f"index{suggested_extension}").relative_to(self.project_path))
                    else:
                        proposed_path = str(target_path.with_suffix(suggested_extension).relative_to(self.project_path))
                    
                    # Generate suggested template based on imported symbols
                    is_component = any(symbol[0].isupper() for symbol in imported_symbols)
                    template = self._generate_template_content(imported_symbols, is_component, suggested_extension.endswith('x'))
                    
                    return FileOperation(
                        success=True,
                        message=f"File not found, should be created at: {proposed_path}",
                        path=proposed_path,
                        suggested_action="create_file",
                        content=template
                    )
                
                return FileOperation(
                    success=False,
                    message=f"Import target not found: {import_path}",
                    path=str(file_path)
                )
                
        except Exception as e:
            return FileOperation(
                success=False,
                message=f"Error analyzing dependencies: {str(e)}",
                path=data["file"]
            )
            
    def _generate_template_content(self, symbols: List[str], is_component: bool, is_react: bool) -> str:
        """Generate template content based on imported symbols."""
        content = []
        
        # Add client directive for React components
        if is_react and is_component:
            content.append('"use client";')
            content.append("")
        
        # Add React import for components
        if is_react:
            content.append('import React from "react";')
            content.append("")
        
        # Generate exports based on symbols
        if is_component:
            # Generate component exports
            for symbol in symbols:
                if symbol[0].isupper():  # Component names start with uppercase
                    content.append(f"export interface {symbol}Props {{")
                    content.append("  // Define your props here")
                    content.append("}")
                    content.append("")
                    content.append(f"export function {symbol}({{ ...props }}: {symbol}Props) {{")
                    content.append("  return (")
                    content.append('    <div className="component">')
                    content.append(f'      <h2>{symbol}</h2>')
                    content.append('      <p>Component implementation</p>')
                    content.append('    </div>')
                    content.append('  );')
                    content.append('}')
                else:
                    # For non-component exports in a component file
                    content.append(f"export const {symbol} = null; // Replace with actual implementation")
        else:
            # Generate non-component exports
            for symbol in symbols:
                if symbol.startswith('type ') or symbol.startswith('interface '):
                    content.append(f"export {symbol} = {{}}; // Replace with actual type definition")
                else:
                    content.append(f"export const {symbol} = null; // Replace with actual implementation")
        
        return "\n".join(content)

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