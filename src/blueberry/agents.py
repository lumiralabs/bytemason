from lumos import lumos
from blueberry.models import Intent, ProjectSpec
import httpx
from rich.console import Console
from rich.prompt import Prompt, Confirm
import json
import os
from openai import OpenAI


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
