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
from typing import List, Dict, Set
import shutil
from rich.progress import SpinnerColumn, TextColumn
import asyncio
from fnmatch import fnmatch
from blueberry.repair_agent import RepairAgent


class ProjectBuilder:
    def __init__(self):
        self.console = Console()
          # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.ai_log_file = (
            log_dir / f"ai_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

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

    def understand_intent(self, user_input: str) -> Intent:
        """Understand the user's intent from the user's input."""
        try:
            prompt = user_input
            intent = lumos.call_ai(
    messages=[
        {
            "role": "system",
            "content": """You are a senior product analyst specializing in web application requirements extraction. Your expertise is in distilling user requests into structured, actionable feature sets that development teams can implement without ambiguity.

            ## YOUR OBJECTIVE
            Transform the user's freeform request into a precise feature set for a Next.js 14 + Supabase application. You must:

            1. Extract only explicitly mentioned or logically necessary features
            2. Never invent or suggest additional features not implied by the request
            3. Identify the minimum viable data model required
            4. Determine authentication boundaries and user types
            5. Recognize technical constraints and limitations

            ## EXTRACTION METHODOLOGY
            When analyzing the user input:

            1. **Core Purpose Analysis**: Identify the fundamental problem the application solves
            2. **User Type Identification**: Determine distinct user roles who will interact with the system
            3. **Feature Extraction**: List only features that are:
            - Explicitly mentioned in the request
            - Logically required for the application to function as described
            - Assign each a priority (Critical/High/Medium) and complexity (Simple/Moderate/Complex)
            4. **Data Model Extraction**: Identify entities that must be stored, with only their essential attributes
            5. **Auth Requirement Analysis**: Determine authentication needs and permission boundaries
            6. **Integration Identification**: Note any external systems the application must connect with
            7. **Constraint Recognition**: Identify limitations that will impact implementation

            ## RESPONSE QUALITY CRITERIA
            - Every feature must be traceable to the user's request or be logically necessary
            - Features must be specific and actionable (e.g., "User authentication with email and password" NOT "User system")
            - Each feature must be discrete and focused on a single capability
            - Avoid marketing language or subjective quality descriptions
            - Never include "nice-to-have" or aspirational features

            Remember: Your output will directly shape the technical specification. Only include what is necessary and clearly implied.
            """,
        },
            {"role": "user", "content": user_input},
        ],
                response_format=Intent,
                model="anthropic/claude-3-5-sonnet-20241022",
            )
            
            # Log the AI response
            self._log_ai_response(prompt, intent.model_dump(), "understand_intent")
            
            return intent

        except Exception as e:
            raise ValueError(f"Failed to understand intent: {str(e)}")

    # def validate_feature(self, feature: str) -> str:
    #     """Validate and enhance a single feature.

    #     Args:
    #         feature: The feature to validate and enhance

    #     Returns:
    #         str: The validated/enhanced feature description
    #     """
    #     system_prompt = """You are an expert in writing clear, specific feature descriptions for web applications.
    #     Given a feature description, enhance it to be more specific and actionable.

    #     Guidelines:
    #     - Make it clear and specific
    #     - Include key functionality aspects
    #     - Consider security and UX implications
    #     - Keep it concise but complete

    #     Example Input: "User authentication"
    #     Example Output: "Email and social authentication with JWT tokens and password reset"
    #     """

    #     _intent = lumos.call_ai(
    #         messages=[
    #             {
    #                 "role": "system",
    #                 "content": system_prompt,
    #             },
    #             {"role": "user", "content": f"Enhance this feature: {feature}"},
    #         ],
    #         response_format=Intent,
    #         model="anthropic/claude-3-5-sonnet-20241022",
    #     )

    #     return feature

    # def verify_with_user_loop(self, intent: Intent, max_attempts=3) -> Intent:
    #     """Verify the intent with the user, iterate with feedback and returns the final intent.

    #     Args:
    #         intent: The initial intent to verify
    #         max_attempts: Maximum number of modification attempts

    #     Returns:
    #         Intent: The verified and potentially modified intent
    #     """

    #     console = Console()

    #     attempts = 0
    #     while attempts < max_attempts:
    #         # Display current features
    #         console.print("\n[bold yellow]Current features:[/bold yellow]")
    #         for i, feature in enumerate(intent.features, 1):
    #             console.print(f"{i}. {feature}")

    #         if not typer.confirm(
    #             "\nWould you like to modify these features?",
    #             default=False,
    #             show_default=True,
    #         ):
    #             break

    #         # Show modification options
    #         console.print("\n[bold]Options:[/bold]")
    #         console.print("1. Add a feature")
    #         console.print("2. Remove a feature")
    #         console.print("3. Done modifying")

    #         choice = Prompt.ask("What would you like to do?", choices=["1", "2", "3"])

    #         if choice == "1":
    #             new_feature = Prompt.ask("Enter new feature")

    #             # Validate and enhance the feature with AI
    #             if typer.confirm(
    #                 "Would you like AI to validate and enhance this feature?",
    #                 default=True,
    #                 show_default=True,
    #             ):
    #                 status = console.status("[bold green]Validating feature...")
    #                 status.start()
    #                 try:
    #                     enhanced_feature = self.validate_feature(new_feature)
    #                     if enhanced_feature != new_feature:
    #                         status.stop()
    #                         if typer.confirm(
    #                             f"Would you like to use the enhanced version: {enhanced_feature}?",
    #                             default=True,
    #                             show_default=True,
    #                         ):
    #                             new_feature = enhanced_feature
    #                     else:
    #                         status.stop()
    #                 except Exception as e:
    #                     status.stop()
    #                     console.print(f"[red]Error validating feature: {e}[/red]")

    #             intent.features.append(new_feature)

    #         elif choice == "2":
    #             if not intent.features:
    #                 console.print("[yellow]No features to remove[/yellow]")
    #                 continue

    #             remove_idx = (
    #                 int(
    #                     Prompt.ask(
    #                         "Enter number of feature to remove",
    #                         choices=[
    #                             str(i) for i in range(1, len(intent.features) + 1)
    #                         ],
    #                     )
    #                 )
    #                 - 1
    #             )
    #             intent.features.pop(remove_idx)

    #         else:  # choice == "3"
    #             break

    #         attempts += 1

    #         # Show updated features
    #         console.print("\n[bold yellow]Updated features:[/bold yellow]")
    #         for i, feature in enumerate(intent.features, 1):
    #             console.print(f"{i}. {feature}")

    #     return intent

    def create_spec(self, intent: Intent) -> ProjectSpec:
        """Create a detailed project specification based on the intent and save it to a file."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, "prompts", "core_prompt.md")

            with open(prompt_path, "r") as f:
                core_prompt = f.read()

            prompt_content = f"Generate specification for: {json.dumps(intent.model_dump(), indent=2)}"
            
            spec = lumos.call_ai(
    messages=[
        {
            "role": "system",
            "content": f"""You are a principal architect with 10+ years of experience specializing in NextJS 14 + Supabase production applications. Your specifications serve as the foundation for entire development teams and must balance technical precision with actionable clarity.

            ## ANALYSIS PHASE
            Begin with a structured risk and feasibility assessment:
            1. **Technical constraints** - Evaluate potential performance bottlenecks, scalability concerns, and dependency risks
            2. **Data complexity** - Assess relationships, migration challenges, and edge cases
            3. **Security considerations** - Identify authentication/authorization boundaries and data exposure risks
            4. **Implementation complexity** - Rate each feature's difficulty (Low/Medium/High) with justification

            ## SPECIFICATION STRUCTURE
            For each feature, provide a specification that includes:

            ### Architecture
            - **Data Flow Diagram** - Show how data moves through the system for this feature
            - **Component Hierarchy** - Outline parent-child relationships with props interfaces
            - **State Management** - Identify global vs. local state needs with recommended patterns

            ### Database Design
            - **Table schemas** with:
            - Column names with data types and constraints
            - Foreign key relationships and cascade behaviors
            - Indexes and performance considerations
            - RLS (Row Level Security) policies for Supabase
            - Triggers and functions when necessary

            ### API Layer
            - **Route specifications** for each endpoint:
            - Full path with method (e.g., POST /api/projects/:id/collaborators)
            - Request body schema with validation rules
            - Response schema with status codes
            - Error handling strategy
            - Rate limiting considerations
            - Authentication/authorization requirements

            ### UI Components
            - **Component breakdown** with:
            - Purpose and responsibility
            - Props interface with TypeScript types
            - State management approach
            - Key user interactions and event handlers
            - Accessibility considerations
            - Reusability potential across the application

            ### Pages
            - **Page routes** with:
            - Dynamic segments and query parameters
            - Data fetching strategy (SSR/SSG/ISR/CSR)
            - SEO considerations
            - Loading/error states
            - Layout components and nested routes

            ### Testing Strategy
            - **Unit test coverage** requirements
            - **Integration test** scenarios
            - **E2E test** critical paths
            - **Performance testing** metrics to monitor

            ### Progressive Enhancement
            - Outline how features can be implemented incrementally
            - Provide fallback strategies for complex features

            Use the existing project structure and best practices from {core_prompt} as foundation.

            Your specification must be optimized for implementation by balancing comprehensiveness with clarity. Focus on technical precision while maintaining readability for junior developers. Avoid theoretical patterns - every element must be implementable in Next.js 14 and Supabase.
            """,
        },
        {
            "role": "user",
            "content": prompt_content,
        },
    ],
    response_format=ProjectSpec,
    model="anthropic/claude-3-5-sonnet-20241022"
)

            # Log the AI prompt and response
            self._log_ai_response(prompt_content, spec.model_dump(), "create_spec")

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
                # Skip .git, .next, .lumos files/folders, .gitignore and ignored patterns
                if (not relative_path.startswith(".git/") and 
                    not relative_path.startswith(".next/") and
                    not relative_path.startswith(".lumos") and
                    not relative_path == ".lumos" and
                    not relative_path == ".gitignore" and
                    not self._should_ignore(relative_path)):
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
                
                # 3. Identify and add shadcn components
                task = progress.add_task("[cyan]Installing shadcn components...", total=None)
                await self._identify_and_add_shadcn_components(generated.files)
                progress.update(task, completed=True)

                # 4. Run build and fix errors
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

    async def _identify_and_add_shadcn_components(self, files: List[FileContent]) -> None:
        """
        Identify shadcn components used in the generated code and add them using the shadcn CLI.
        """
        component_pattern = r'from\s+[\'"]@/components/ui/([a-z0-9-]+)[\'"]'
        components: Set[str] = set()
        
        # 1. Scan all files for shadcn component imports
        for file in files:
            if file.path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                matches = re.findall(component_pattern, file.content)
                components.update(matches)
        
        if not components:
            self.console.print("[dim]No shadcn components found to install[/dim]")
            return
            
        self.console.print(f"[cyan]Found {len(components)} shadcn components to install:[/cyan]")
        for comp in sorted(components):
            self.console.print(f"[dim]- {comp}[/dim]")
        
        # 2. Install each component
        for component in sorted(components):
            try:
                self.console.print(f"[cyan]Installing shadcn component: {component}[/cyan]")
                
                # Fixed command: use shadcn@latest instead of shadcn-ui@latest and -y instead of --yes
                process = await asyncio.create_subprocess_exec(
                    "npx", 
                    "shadcn@latest",
                    "add",
                    component,
                    "-y",  # Use -y instead of --yes for the flag
                    cwd=str(self.project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                # Log the full output for debugging
                stdout_text = stdout.decode().strip() if stdout else ""
                stderr_text = stderr.decode().strip() if stderr else ""

                self.console.print(f"[dim]shadcn output: {stdout_text}[/dim]")
                self.console.print(f"[dim]shadcn error: {stderr_text}[/dim]")
                
                if process.returncode == 0:
                    self.console.print(f"[green]Successfully installed {component}[/green]")
                else:
                    self.console.print(f"[yellow]Error installing {component}[/yellow]")
                    
            except Exception as e:
                self.console.print(f"[yellow]Error installing {component}: {str(e)}[/yellow]")

    async def _generate_structured_code(self) -> GeneratedCode:
        """Generate code with maximum context flow: API -> Components -> Pages"""
        try:
            all_files = []
            
            # Get core prompt
            current_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(current_dir, "prompts", "core_prompt.md"), "r") as f:
                core_prompt = f.read()
            
            # 1. Generate API routes first
            api_files = await self._generate_api_routes(core_prompt)
            if api_files and len(api_files) > 0:
                all_files.extend(api_files)
            
            # 2. Generate components with API context
            component_files = await self._generate_components(core_prompt, api_files or [])
            if component_files and len(component_files) > 0:
                all_files.extend(component_files)
            
            # 3. Generate pages with full context
            page_files = await self._generate_pages(core_prompt, api_files or [], component_files or [])
            if page_files and len(page_files) > 0:
                all_files.extend(page_files)
            
            if not all_files:
                raise ValueError("No files were generated")
            
            return GeneratedCode(files=all_files, dependencies=[], errors=[])

        except Exception as e:
            self.console.print(f"[red]Error in code generation: {str(e)}[/red]")
            # Return empty GeneratedCode with error instead of raising
            return GeneratedCode(
                files=[],
                dependencies=[],
                errors=[f"Code generation failed: {str(e)}"]
            )

    async def _generate_api_routes(self, core_prompt: str) -> List[FileContent]:
        """Generate all API routes with database context"""
        try:
            prompt = f"""As a Next.js 14 Route Handler specialist, generate all API routes.

            Critical Requirements:
            1. Use Route Handlers (app/api/*/route.ts), NOT pages/api
            2. Each handler must:
               - Use proper HTTP methods (GET, POST, PUT, DELETE)
               - Have proper TypeScript types for request/response
               - Include error handling with appropriate status codes
               - don't use any ORM, just use the normal supabase client
               - ALWAYS return complete entity data after mutations for client-side state updates
            3. Follow these patterns:
               - Use NextResponse from 'next/server'
               - Handle authentication via middleware (already implemented)
               - Include proper CORS headers where needed
               - Use edge runtime where beneficial
            4. Security considerations:
               - Validate all inputs
               - Check user permissions
               - Sanitize responses

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

            CRITICAL: Your response MUST be in this EXACT JSON format:
                    {{
                        "files": [
                            {{
                                "path": "string (e.g., app/api/example/route.ts)",
                                "content": "string (the complete file content)", 
                                "mode": "create",
                                "modify_strategy": null   # null if the file is new, only write if the file already exists
                            }}
                        ],
                        "dependencies": [], # npm dependencies if any
                        "errors": []
                    }}

            Spec:
            {json.dumps(self.spec.model_dump(), indent=2)}
            
            {core_prompt}
            """
            
            
            response = await lumos.call_ai_async(
                messages=[
                    {"role": "system", "content": "You are a Next.js 14 Route Handler specialist focusing on type-safety and security."},
                    {"role": "user", "content": prompt}
                ],
                response_format=GeneratedCode,
                model="anthropic/claude-3-5-sonnet-20241022"
            )
            
            # Add validation logging
            self.console.print(f"[dim]Debug: API generation response type: {type(response)}[/dim]")
            self.console.print(f"[dim]Debug: Response content: {response.model_dump()}[/dim]")
            
            # Log the AI prompt and response
            self._log_ai_response(prompt, response.model_dump(), "api_routes")
            
            if not hasattr(response, 'files'):
                self.console.print("[red]Error: Response missing 'files' attribute[/red]")
                return []
            
            return response.files or []

        except Exception as e:
            self.console.print(f"[red]Error in API route generation: {str(e)}[/red]")
            return []

    async def _generate_components(self, core_prompt: str, api_files: List[FileContent]) -> List[FileContent]:
        """Generate components with API context"""
        try:
            api_context = "\n\n".join(f"// {f.path}\n{f.content}" for f in api_files)
            
            prompt = f"""As a Next.js 14 Component architect, generate all React components.

            Critical Requirements:
            1. Component Location:
               - ALL components MUST be in components/ directory
               - Group by feature (e.g., components/todos/, components/profile/)
               - NO components in app/ directory
               
            2. Component Architecture:
               - Use "use client" for ANY component that requires interactivity
               - Client Components are REQUIRED for:
                   * Any user interactions (forms, buttons, toggles)
                   * Any state that needs to update in response to user actions
                   * Any component that makes API calls and updates UI
               - Server Components for static or initial data display only
               - Use shadcn/ui components from @/components/ui/
               
            3. Data Handling:
               - For ANY mutable data, implement these patterns:
                 * Store entities in local state with useState
                 * Update state IMMEDIATELY after user actions (before API calls)
                 * Call APIs after state updates, not before
                 * Handle API errors with rollback patterns
               - Use createClient() from '@/libs/supabase/server' for server components
               - Use createClient() from '@/libs/supabase/client' for client components
               - Implement proper loading states
               - Handle errors gracefully
               - No need to generate components for any auth pattern like signin signout etc.

            4. Common Patterns for ALL interactive components:
                - Create/Update: Update local state first, then call API
                - Delete: Remove from local state first, then call API
                - Toggle/Status Change: Update UI first, then persist via API
                - Lists: Always use unique "key" props and optimistic updates
                - Forms: Control form state locally, submit with optimistic feedback
               
            Example Interactive Component Pattern (applicable to ANY entity type):
            ```typescript
            'use client';
            
            import {{ useState }} from 'react';
            import {{ Button }} from '@/components/ui/button';
            
            interface EntityProps {{
            initialEntities: any[];
            }}
            
            export default function EntityManager({{ initialEntities }}: EntityProps) {{
            // Local state management - critical for immediate UI updates
            const [entities, setEntities] = useState(initialEntities);
            
            // Create operation pattern
            async function createEntity(newEntityData: any) {{
                // 1. Generate temporary ID for optimistic UI
                const tempId = Date.now().toString();
                
                // 2. Update UI immediately with optimistic data
                const optimisticEntity = {{ id: tempId, ...newEntityData }};
                setEntities(prev => [...prev, optimisticEntity]);
                
                // 3. Call API to persist
                try {{
                const response = await fetch('/api/entities', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(newEntityData),
                }});
                
                const {{ data }} = await response.json();
                
                // 4. Update with real server data
                setEntities(prev => prev.map(entity => 
                    entity.id === tempId ? data : entity
                ));
                }} catch (error) {{
                // 5. Rollback on error
                setEntities(prev => prev.filter(entity => entity.id !== tempId));
                // Handle error notification
                }}
            }}
            
            // Similar patterns for update and delete operations
            // [Implementation details would vary by entity type]
            }}
            ```

            Available Route Handlers:
            {api_context}

            CRITICAL: Your response MUST be in this EXACT JSON format:
                    {{
                        "files": [
                            {{
                                "path": "string (e.g., components/example/ExampleComponent.tsx)",
                                "content": "string (the complete file content)", 
                                "mode": "create",
                                "modify_strategy": null   # null if the file is new, only write if the file already exists
                            }}
                        ],
                        "dependencies": [], # npm dependencies if any
                        "errors": []
                    }}

            Spec:
            {json.dumps(self.spec.model_dump(), indent=2)}
            
            {core_prompt}
            """
        
            
            response = await lumos.call_ai_async(
                messages=[
                    {"role": "system", "content": "You are a Next.js 14 Component architect specializing in Server and Client Components."},
                    {"role": "user", "content": prompt}
                ],
                response_format=GeneratedCode,
                model="anthropic/claude-3-5-sonnet-20241022"
            )
            
            # Add validation logging
            self.console.print(f"[dim]Debug: Component generation response type: {type(response)}[/dim]")
            self.console.print(f"[dim]Debug: Response content: {response.model_dump()}[/dim]")
            
            # Log the AI prompt and response
            self._log_ai_response(prompt, response.model_dump(), "components")
            
            if not hasattr(response, 'files'):
                self.console.print("[red]Error: Response missing 'files' attribute[/red]")
                return []
            
            return response.files or []

        except Exception as e:
            self.console.print(f"[red]Error in component generation: {str(e)}[/red]")
            return []

    async def _generate_pages(
        self, 
        core_prompt: str,
        api_files: List[FileContent],
        component_files: List[FileContent]
    ) -> List[FileContent]:
        """Generate pages with full context"""
        try:
            context = {
                'api': "\n\n".join(f"// {f.path}\n{f.content}" for f in api_files),
                'components': "\n\n".join(f"// {f.path}\n{f.content}" for f in component_files)
            }
            
            prompt = f"""As a Next.js 14 App Router specialist, generate all necessary pages in strict accordance with the following guidelines.

                    Critical Requirements:
                    1. File & Folder Structure:
                    - All pages must reside within the 'app/' directory.
                    - Use 'page.tsx' for public routes.
                    - Include 'layout.tsx' for shared layout.
                    - Provide a landing page at 'app/page.tsx'.
                    2. Page Architecture:
                    - Default to Client Components.
                    - All necessary components must be imported from '@/components/' using correct aliasing.
                    - Ensure proper use of Next.js navigation (e.g., useRouter from 'next/navigation').
                    3. Data Flow & Best Practices:
                    - Fetch data within Server Components and pass it as props.
                    - Implement suspense boundaries and proper loading states.
                    - Validate all client interactions, incorporating appropriate auth checks where needed.
                    4. Example Page Structure:
                    ```typescript
                    import {{ createClient }} from '@/libs/supabase/server';
                    import TodoList from '@/components/todos/TodoList';

                    export default async function DashboardPage() {{
                    const supabase = createClient()
                    // Fetch page-specific data
                    return <TodoList />
                    }}
                    ```
                    5. landing page is app/page.tsx
                    - create a good landing page with a nice UI/UX, it should have buttons and features to navigate to the main app, if there is a component for the landing page, use it.

                    Validation Checklist:
                    - Verify that the file structure adheres to Next.js 14 App Router conventions.
                    - Ensure that every referenced component is imported with the correct alias.
                    - Ensure that the landing page is created at app/page.tsx
                    - Ensure that all the created components are used at least once in a page
                    - Confirm the existence of key files (layout.tsx, page.tsx) in the proper locations.

                    Available Components:
                    {context['components']}

                    Available Route Handlers:
                    {context['api']}

                    CRITICAL: Your response MUST be in this EXACT JSON format:
                    {{
                        "files": [
                            {{
                                "path": "string (e.g., app/example/ExamplePage.tsx)",
                                "content": "string (the complete file content)", 
                                "mode": "create",
                                "modify_strategy": null   # null if the file is new, only write if the file already exists
                            }}
                        ],
                        "dependencies": [], # npm dependencies if any
                        "errors": []
                    }}

                    Spec:
                    {json.dumps(self.spec.model_dump(), indent=2)}

                    {core_prompt}
                    """
            
            

            
            response = await lumos.call_ai_async(
                messages=[
                    {"role": "system", "content": "You are a Next.js 14 App Router specialist focusing on proper page structure and data flow."},
                    {"role": "user", "content": prompt}
                ],
                response_format=GeneratedCode,
                model="anthropic/claude-3-5-sonnet-20241022"
            )
            
            # Add validation logging
            self.console.print(f"[dim]Debug: Page generation response type: {type(response)}[/dim]")
            self.console.print(f"[dim]Debug: Response content: {response.model_dump()}[/dim]")
            
            # Log the AI prompt and response
            self._log_ai_response(prompt, response.model_dump(), "pages")
            
            if not hasattr(response, 'files'):
                self.console.print("[red]Error: Response missing 'files' attribute[/red]")
                return []
            
            return response.files or []

        except Exception as e:
            self.console.print(f"[red]Error in page generation: {str(e)}[/red]")
            return []

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
                        self.console.print(
                            f"[yellow]Build failed with {len(errors.errors)} errors[/yellow]"
                        )
                        for error in errors.errors:
                            self.console.print(
                                f"[red]Error in {error.file}: {error.message}[/red]"
                            )
                        return errors.errors
                except Exception as e:
                    self.console.print(
                        f"[yellow]AI error analysis failed, falling back to basic parsing: {str(e)}[/yellow]"
                    )
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
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing Next.js and TypeScript build errors.",
                    },
                    {"role": "user", "content": prompt},
                ],
                model="anthropic/claude-3-5-sonnet-20241022",
                response_format=BuildErrorReport,
            )

            # Log the AI prompt and response
            self._log_ai_response(prompt, response.model_dump(), "build_error_analysis")

            print(response)

            return response

        except Exception as e:
            self.console.print(f"[yellow]AI error analysis failed: {str(e)}[/yellow]")
            return []

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
                        4. Do not include any RLS policies
                        
                        Format as a single SQL file with proper ordering of operations. dont include any other text no markdown, no dummy data, just code. Do not wrap the code in ```sql tags.""",
                    },
                    {
                        "role": "user",
                        "content": f"Generate pgsql migration for: {json.dumps(self.spec.model_dump(), indent=2)}",
                    },
                ],
                model="anthropic/claude-3-5-sonnet-20241022",
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
SUPABASE_SERVICE_ROLE_KEY={service_key}"""

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
