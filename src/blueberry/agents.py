from lumos import lumos
from blueberry.models import Intent, ProjectSpec
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
import json
import os
from openai import OpenAI
from langchain_openai import ChatOpenAI
from codegen import Codebase
from codegen.extensions.langchain.agent import create_codebase_agent
from codegen.extensions.langchain.tools import (
    ViewFileTool,
    ListDirectoryTool,
    SearchTool,
    EditFileTool,
    CreateFileTool,
    DeleteFileTool,
    RenameFileTool,
    MoveSymbolTool,
    RevealSymbolTool,
    SemanticEditTool,
    CommitTool
)
from pathlib import Path
import shutil


class MasterAgent:
    def __init__(self):
        pass

    def understand_intent(self, user_input: str) -> Intent:
        """
        Understand the user's intent from the user's input, and returns a more detailed intent with features, components, etc.
        """
        system_prompt = """Analyze user requests for Next.js + Supabase applications and break them down into core features.

        Focus on:
        1. Core functionality and key features
        2. Required auth/security features
        3. Essential data models
        4. Critical API endpoints

        Format features as specific, actionable items like:
        - "Email and social authentication"
        - "Real-time chat messaging"
        - "File upload with image optimization"

        Consider security, performance, and user experience in your analysis."""
        
        intent = lumos.call_ai(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": user_input},
            ],
            response_format=Intent,
            model="gpt-4o-mini",
        )
        
        # Ensure we have a name and description
        if not intent.name:
            intent.name = user_input.strip().lower().replace(" ", "-")
        if not intent.description:
            intent.description = f"A Next.js application that {user_input}"
            
        return intent

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
        """Create a detailed project specification based on the intent and preferences.
        
        Args:
            intent: The intent object containing project requirements and preferences.
            
        Returns:
            ProjectSpec: A detailed project specification ready for implementation.
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required")
            
        client = OpenAI()
        console = Console()
        
        console.log('🚀 [Spec Generation] Processing intent:', intent.model_dump_json())
        
        try:
            console.log('📡 [Spec Generation] Making OpenAI API call...')
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert full-stack developer specializing in Next.js and Supabase applications. Generate a detailed specification for a web application based on the user's prompt.
                        
                        The specification should follow this exact structure:
                        {
                          "project": {
                            "name": "string - use the intent name",
                            "description": "string - use the intent description",
                            "techStack": ["Next.js 14", "Supabase", "TypeScript", "Tailwind CSS", ...]
                          },
                          "frontendStructure": {
                            "pages": {
                              "/path": {
                                "type": "SSR|Static|SSG",
                                "components": ["array of components"],
                                "authRequired": boolean,
                                "dataFetching": ["data to fetch"]
                              }
                            },
                            "components": {
                              "shared": ["reusable components"],
                              "feature": ["feature-specific components"]
                            }
                          },
                          "apiRoutes": {
                            "group": {
                              "/api/path": {
                                "method": "HTTP method",
                                "middleware": ["auth checks"],
                                "supabase": "supabase query",
                                "validation": ["required fields"]
                              }
                            }
                          },
                          "supabaseConfig": {
                            "tables": {
                              "tableName": {
                                "columns": {"column": "type"},
                                "RLS": {"policy": "condition"}
                              }
                            },
                            "indexes": ["SQL index statements"]
                          },
                          "features": {
                            "category": ["feature list - use intent features"]
                          },
                          "dependencies": {
                            "required": ["prod dependencies"],
                            "dev": ["dev dependencies"]
                          },
                          "environmentVariables": {
                            "VAR_NAME": "type"
                          },
                          "acceptanceCriteria": [
                            "list of criteria"
                          ]
                        }

                        Important:
                        1. Use the intent.name for project.name
                        2. Use the intent.description for project.description
                        3. Use the intent.features to populate the features section
                        4. If intent.preferences exist, use them to customize the specification
                        
                        Guidelines:
                        1. Always include authentication and authorization
                        2. Use TypeScript and modern React patterns
                        3. Implement proper security measures
                        4. Consider performance optimizations
                        5. Follow Next.js best practices for routing and data fetching
                        6. Include proper error handling
                        7. Add comprehensive validation
                        8. Consider real-time features where appropriate"""
                    },
                    {
                        "role": "user",
                        "content": f"Generate a JSON specification for the following app: {json.dumps(intent.model_dump(), indent=2)}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            console.log('✅ [Spec Generation] OpenAI API call successful')

            message = completion.choices[0].message
            if not message.content:
                console.log('❌ [Spec Generation] No valid response from OpenAI')
                raise ValueError("Failed to generate specification: Empty response from OpenAI")

            try:
                spec_dict = json.loads(message.content)
                console.log('✨ [Spec Generation] Parsed JSON response')
                
                # Ensure project name and description are set from intent
                if "project" not in spec_dict:
                    spec_dict["project"] = {}
                spec_dict["project"]["name"] = intent.name
                spec_dict["project"]["description"] = intent.description
                
                spec = ProjectSpec.model_validate(spec_dict)
                console.log('🎉 [Spec Generation] Validated specification schema')
                return spec
                
            except json.JSONDecodeError as e:
                console.log('💥 [Spec Generation] Failed to parse JSON response')
                raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")
            except Exception as e:
                console.log('💥 [Spec Generation] Failed to validate specification')
                raise ValueError(f"Invalid specification format: {str(e)}")
            
        except Exception as e:
            console.log('💥 [Spec Generation] Error:', str(e))
            raise


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
        self.project_path = project_path
            
        # Change to the project directory
        os.chdir(self.project_path)
        
        # Initialize codebase with the local project directory
        self.codebase = Codebase(".")
        
        # Log initialization
        self.console.print(f"[green]Initialized CodeAgent with project at: {self.project_path}[/green]")
        
        # Create tools
        self.tools = [
            ViewFileTool(self.codebase),
            ListDirectoryTool(self.codebase),
            SearchTool(self.codebase),
            EditFileTool(self.codebase),
            CreateFileTool(self.codebase),
            DeleteFileTool(self.codebase),
            RenameFileTool(self.codebase),
            MoveSymbolTool(self.codebase),
            RevealSymbolTool(self.codebase),
            SemanticEditTool(self.codebase),
            CommitTool(self.codebase)
        ]
        
        # Create the agent
        self.agent = create_codebase_agent(
            codebase=self.codebase,
            model_name="gpt-4o",
            temperature=0,
            verbose=True,
        )
        
        # Create session config
        self.session_config = {
            "configurable": {
                "session_id": self.spec.project.name
            }
        }
        
    async def transform_template(self):
        """Transform the template into the final application based on spec."""
        steps = {
            "Cleaning up template": self._cleanup_template,
            "Setting up database": self._setup_database,
            "Configuring authentication": self._setup_auth,
            "Creating API routes": self._create_api_routes,
            "Generating components": self._create_components,
            "Creating pages": self._create_pages,
            "Setting up styles": self._setup_styles,
            "Configuring environment": self._configure_environment
        }
        
        for description, step_func in steps.items():
            with self.console.status(f"[bold green]{description}..."):
                try:
                    await step_func()
                except Exception as e:
                    self.console.print(f"[red]Error in {step_func.__name__}: {str(e)}[/red]")
                    raise
                    
    async def _cleanup_template(self):
        """Remove tutorial and example files."""
        try:
            # Use agent to analyze and remove files
            result = self.agent.invoke(
                {
                    "input": """Analyze the codebase and remove all tutorial and example files.
                    This includes any demo components, example routes, and tutorial content.
                    
                    Also clean up the layout.tsx file by removing any tutorial-related imports and components."""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Cleaned up template files[/green]")
            else:
                raise Exception("Failed to clean up template")
        except Exception as e:
            self.console.print(f"[red]Error cleaning up template: {str(e)}[/red]")
            raise
        
    async def _setup_database(self):
        """Set up Supabase database schema."""
        try:
            # Create migrations directory
            migrations_dir = "supabase/migrations"
            
            # Use agent to set up database schema
            result = self.agent.invoke(
                {
                    "input": f"""Create a Supabase database schema with the following configuration:
                    {json.dumps(self.spec.supabaseConfig.model_dump(), indent=2)}
                    
                    Requirements:
                    1. Create a migration file at {migrations_dir}/00000000000000_initial.sql
                    2. Use Supabase SQL syntax
                    3. Include RLS policies
                    4. Add appropriate indexes
                    5. Add timestamps and primary keys
                    6. Set up foreign key relationships
                    7. Enable RLS on all tables"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Generated database schema[/green]")
            else:
                raise Exception("Failed to generate database schema")
        except Exception as e:
            self.console.print(f"[red]Error setting up database: {str(e)}[/red]")
            raise
        
    async def _setup_auth(self):
        """Configure authentication."""
        try:
            # Use agent to set up authentication
            result = self.agent.invoke(
                {
                    "input": f"""Set up Next.js authentication with Supabase.
                    
                    Create and configure the following files:
                    1. app/lib/auth.ts - Server-side auth utilities
                    2. middleware.ts - Auth middleware
                    3. app/lib/client.ts - Client-side auth utilities
                    
                    Requirements:
                    1. Use Next.js App Router
                    2. Implement server-side auth with cookies
                    3. Add client-side auth utilities
                    4. Handle session refresh
                    5. Add middleware for protected routes
                    6. Support the following auth methods: {self.spec.project.techStack}
                    7. Add proper TypeScript types
                    8. Add proper error handling
                    9. Add proper documentation"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Set up authentication[/green]")
            else:
                raise Exception("Failed to set up authentication")
        except Exception as e:
            self.console.print(f"[red]Error setting up authentication: {str(e)}[/red]")
            raise
        
    async def _create_api_routes(self):
        """Generate API routes."""
        try:
            # Use agent to create API routes
            result = self.agent.invoke(
                {
                    "input": f"""Create Next.js API routes with the following configuration:
                    {json.dumps(self.spec.apiRoutes, indent=2)}
                    
                    Requirements:
                    1. Create route handlers in the app directory following Next.js App Router conventions
                    2. Implement proper error handling
                    3. Add request validation
                    4. Include authentication middleware where required
                    5. Use Supabase client for database operations
                    6. Add proper TypeScript types
                    7. Follow REST best practices
                    8. Add rate limiting where appropriate
                    9. Include API documentation comments
                    10. Add proper testing setup"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Created API routes[/green]")
            else:
                raise Exception("Failed to create API routes")
        except Exception as e:
            self.console.print(f"[red]Error creating API routes: {str(e)}[/red]")
            raise
                
    async def _create_components(self):
        """Generate React components."""
        try:
            # Use agent to create components
            result = self.agent.invoke(
                {
                    "input": f"""Create React components with the following configuration:
                    {json.dumps(self.spec.frontendStructure.components, indent=2)}
                    
                    Requirements:
                    1. Create components in the components directory organized by category
                    2. Use React Server Components where appropriate
                    3. Implement proper TypeScript types
                    4. Use Tailwind CSS for styling
                    5. Add proper error boundaries
                    6. Include loading states
                    7. Add proper accessibility attributes
                    8. Use modern React patterns (hooks, context, etc.)
                    9. Add proper documentation and comments
                    10. Include unit tests
                    11. Use shadcn/ui components where applicable
                    12. Add storybook stories for each component"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Created React components[/green]")
            else:
                raise Exception("Failed to create components")
        except Exception as e:
            self.console.print(f"[red]Error creating components: {str(e)}[/red]")
            raise
                
    async def _create_pages(self):
        """Generate Next.js pages."""
        try:
            # Use agent to create pages
            result = self.agent.invoke(
                {
                    "input": f"""Create Next.js pages with the following configuration:
                    {json.dumps(self.spec.frontendStructure.pages, indent=2)}
                    
                    Requirements:
                    1. Create pages in the app directory following Next.js App Router conventions
                    2. Add loading.tsx and error.tsx for each page with data fetching
                    3. Implement proper data fetching using Supabase
                    4. Add loading and error states
                    5. Use proper TypeScript types
                    6. Implement proper SEO metadata
                    7. Add proper accessibility
                    8. Use layout components where appropriate
                    9. Implement proper client-side interactions
                    10. Add proper documentation
                    11. Use proper routing patterns
                    12. Handle authentication requirements
                    13. Implement proper data mutations
                    14. Add proper testing setup"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Created Next.js pages[/green]")
            else:
                raise Exception("Failed to create pages")
        except Exception as e:
            self.console.print(f"[red]Error creating pages: {str(e)}[/red]")
            raise
            
    async def _setup_styles(self):
        """Set up styling configuration."""
        try:
            # Use agent to set up styles
            result = self.agent.invoke(
                {
                    "input": f"""Set up styling configuration for the Next.js app.
                    
                    Create and configure the following files:
                    1. tailwind.config.js - Tailwind configuration
                    2. app/globals.css - Global styles
                    3. components/ui/theme.ts - Theme configuration
                    
                    Requirements:
                    1. Configure Tailwind CSS with:
                       - Dark mode support
                       - Custom color scheme
                       - Typography plugin
                       - Forms plugin
                       - Animations
                    2. Set up global styles with:
                       - CSS reset
                       - Custom variables
                       - Utility classes
                       - Component styles
                    3. Configure theme based on: {self.spec.project.techStack}
                    4. Add shadcn/ui configuration
                    5. Set up responsive design utilities
                    6. Add custom animations
                    7. Add proper TypeScript types for theme
                    8. Add color scheme configuration
                    9. Set up CSS variables for theming"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Set up styling configuration[/green]")
            else:
                raise Exception("Failed to set up styles")
        except Exception as e:
            self.console.print(f"[red]Error setting up styles: {str(e)}[/red]")
            raise
            
    async def _configure_environment(self):
        """Set up environment variables."""
        try:
            # Use agent to configure environment
            result = self.agent.invoke(
                {
                    "input": f"""Set up environment configuration for the Next.js app.
                    
                    Create and configure the following files:
                    1. .env.local.example - Example environment variables
                    2. .env.development - Development environment variables
                    3. .env.test - Test environment variables
                    4. app/lib/env.ts - Environment validation
                    
                    Environment variables to configure:
                    {json.dumps(self.spec.environmentVariables, indent=2)}
                    
                    Requirements:
                    1. Set up proper environment variables
                    2. Add proper validation using zod
                    3. Include development defaults
                    4. Add test environment setup
                    5. Include proper documentation
                    6. Add TypeScript types
                    7. Set up environment validation
                    8. Add proper security measures
                    9. Add proper error messages
                    10. Handle different environments (development, test, production)"""
                },
                config=self.session_config
            )
            
            if result:
                self.console.print("[green]✓ Set up environment configuration[/green]")
            else:
                raise Exception("Failed to set up environment")
        except Exception as e:
            self.console.print(f"[red]Error configuring environment: {str(e)}[/red]")
            raise
