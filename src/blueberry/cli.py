import typer
from typing import Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
import subprocess
from blueberry.agents import MasterAgent, CodeAgent
from blueberry.models import ProjectSpec
import asyncio
import os

app = typer.Typer()
console = Console()

PREFERENCE_QUESTIONS = [
    {
        "key": "auth_setup",
        "question": "How would you like to handle authentication?",
        "options": [
            "No authentication needed",
            "Email/Password only",
            "Social logins (Google, GitHub)",
            "Magic link authentication",
            "Full auth (Email + Social + Magic link)"
        ],
        "default": "Email/Password only"
    },
    {
        "key": "theme_style",
        "question": "What color theme would you prefer?",
        "options": [
            "Light mode only",
            "Dark mode only",
            "Light/Dark mode toggle",
            "System preference based"
        ],
        "default": "Light/Dark mode toggle"
    },
    {
        "key": "color_scheme",
        "question": "Choose a base color scheme:",
        "options": [
            "Blue (Professional)",
            "Green (Fresh/Natural)",
            "Purple (Creative)",
            "Orange (Energetic)",
            "Neutral (Minimal)",
            "Custom (You can modify later)"
        ],
        "default": "Blue (Professional)"
    },
    {
        "key": "layout_type",
        "question": "What type of layout would you prefer?",
        "options": [
            "Simple (Header + Content)",
            "Dashboard (Sidebar + Header)",
            "Landing Page Style",
            "Custom (Complex layout)"
        ],
        "default": "Simple (Header + Content)"
    },
    {
        "key": "responsive_priority",
        "question": "What's your responsive design priority?",
        "options": [
            "Mobile-first",
            "Desktop-first",
            "Tablet-focused",
            "Equal priority to all devices"
        ],
        "default": "Mobile-first"
    },
    {
        "key": "data_loading",
        "question": "How would you like to handle data loading?",
        "options": [
            "Static (Build-time)",
            "Server-side rendering",
            "Client-side fetching",
            "Incremental static regeneration"
        ],
        "default": "Server-side rendering"
    }
]

def display_features(features: List[str]):
    """Display features in a nice formatted way"""
    feature_panels = [Panel(f"✨ {feature}", expand=True) for feature in features]
    console.print(Columns(feature_panels))

def display_spec(spec: ProjectSpec):
    """Display the complete specification in a structured way"""
    console.print("\n[bold blue]📋 Project Specification[/bold blue]")
    
    # Project Overview
    overview = Table(show_header=False, box=None)
    overview.add_row("[bold]Name:[/bold]", spec.name)
    overview.add_row("[bold]Description:[/bold]", spec.description)
    overview.add_row("[bold]Tech Stack:[/bold]", ", ".join(spec.tech_stack))
    console.print(Panel(overview, title="Project Overview", border_style="blue"))
    
    # Components
    components_table = Table(show_header=True)
    components_table.add_column("Name", style="cyan")
    components_table.add_column("Description", style="white")
    components_table.add_column("Dependencies", style="yellow")
    
    for component in spec.structure.components:
        components_table.add_row(
            component.name,
            component.description,
            "\n".join(component.dependencies)
        )
    console.print(Panel(components_table, title="Components", border_style="magenta"))
    
    # API Routes
    api_table = Table(show_header=True)
    api_table.add_column("Path", style="cyan")
    api_table.add_column("Method", style="green")
    api_table.add_column("Description", style="white")
    api_table.add_column("Auth", style="yellow")
    
    for route in spec.structure.api_routes:
        api_table.add_row(
            route.path,
            route.method,
            route.description,
            "Required" if route.auth_required else "Public"
        )
    console.print(Panel(api_table, title="API Routes", border_style="green"))
    
    # Database Tables
    db_table = Table(show_header=True)
    db_table.add_column("Table", style="cyan")
    db_table.add_column("Columns", style="white")
    db_table.add_column("Relationships", style="yellow")
    
    for table in spec.structure.database:
        columns = "\n".join([f"{col}: {type}" for col, type in table.columns.items()])
        relationships = "\n".join(table.relationships) if table.relationships else ""
        db_table.add_row(table.name, columns, relationships)
    
    console.print(Panel(db_table, title="Database Schema", border_style="yellow"))
    
    # Environment Variables
    env_table = Table(show_header=True)
    env_table.add_column("Variable", style="cyan")
    env_table.add_column("Type", style="white")
    
    for var, type in spec.structure.env_vars.items():
        env_table.add_row(var, type)
    console.print(Panel(env_table, title="Environment Variables", border_style="green"))
    
    # Features
    features_table = Table(show_header=False, box=None)
    for feature in spec.features:
        features_table.add_row(f"✓ {feature}")
    console.print(Panel(features_table, title="Features", border_style="blue"))

def get_user_preferences() -> dict:
    """Get user preferences through interactive prompts"""
    preferences = {
        "framework": "Next.js",
        "database": "Supabase",
        "styling": "Tailwind CSS",
        "ui": "shadcn/ui"
    }
    
    console.print("\n[bold blue]🛠️  Let's customize your Next.js + Supabase project[/bold blue]")
    
    for question in PREFERENCE_QUESTIONS:
        console.print(f"\n[cyan]{question['question']}[/cyan]")
        for i, option in enumerate(question['options'], 1):
            console.print(f"{i}. {option}")
        
        choice = Prompt.ask(
            "Choose an option",
            choices=[str(i) for i in range(1, len(question['options']) + 1)],
            default="1"
        )
        preferences[question['key']] = question['options'][int(choice) - 1]
    
    # Get shadcn/ui components based on layout type
    if preferences['layout_type'] == "Simple (Header + Content)":
        preferences['shadcn_components'] = ["button", "form", "input", "card", "dialog", "dropdown-menu", "navigation-menu"]
    elif preferences['layout_type'] == "Dashboard (Sidebar + Header)":
        preferences['shadcn_components'] = ["button", "form", "input", "table", "card", "dialog", 
                                          "command", "navigation-menu", "dropdown-menu", "tabs", 
                                          "accordion", "sidebar"]
    elif preferences['layout_type'] == "Landing Page Style":
        preferences['shadcn_components'] = ["button", "card", "carousel", "navigation-menu", "dialog",
                                          "hover-card", "scroll-area", "tabs", "animation"]
    else:
        preferences['shadcn_components'] = "all"
    
    # Add theme configuration
    preferences['theme'] = {
        'style': preferences.pop('theme_style'),
        'color_scheme': preferences.pop('color_scheme'),
        'responsive_priority': preferences.pop('responsive_priority')
    }
    
    return preferences

@app.command()
def main(
    code: Optional[str] = typer.Option(None, "--code", help="The prompt to process")
):
    """
    Blueberry CLI - Process code generation prompts
    """
    asyncio.run(async_main(code))

async def async_main(code: Optional[str]):
    """
    Async main function to handle coroutines
    """
    if not code:
        console.print("[red]Please provide a prompt using --code flag[/red]")
        raise typer.Exit()

    # Get project name from user
    project_name = Prompt.ask(
        "\n[cyan]What would you like to name your project?[/cyan]",
        default="my-app"
    ).lower().replace(' ', '-')

    # Step 1: Understand Intent
    with console.status("[bold green]Understanding your requirements...") as status:
        agent = MasterAgent()
        intent = agent.understand_intent(code)
    
    # Display features
    console.print("\n[bold blue]Based on your prompt, we'll build the following features:[/bold blue]")
    display_features(intent.features)
    
    # Step 2: Verify and modify features with user
    intent = agent.verify_with_user_loop(intent)
    
    # Step 3: Generate Specification
    try:
        with console.status("[bold green]Generating detailed specification...") as status:
            spec = agent.create_spec(intent)
            status.stop()
            
        console.print("\n[bold green]✨ Specification generated successfully![/bold green]")
        
        # Ask user to proceed with project creation
        if Confirm.ask("\nWould you like to proceed with creating the project?"):
            # Clone the boilerplate repository
            with console.status("[bold green]Cloning boilerplate repository...") as status:
                try:
                    # Clone the repository
                    subprocess.run(
                        ['git', 'clone', 'https://github.com/iminoaru/boilerplate.git', project_name],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    # Get absolute path of the project
                    project_path = os.path.abspath(project_name)
                    status.stop()
                    console.print(f"\n[bold green]✨ Boilerplate cloned successfully to: {project_path}[/bold green]")
                    
                    # Initialize CodeAgent and transform the template
                    console.print("\n[bold blue]Transforming template into your application...[/bold blue]")
                    code_agent = CodeAgent(project_path, spec)
                    await code_agent.transform_template()
                    
                    # Show next steps
                    console.print("\n[bold blue]Next steps:[/bold blue]")
                    console.print("1. cd", project_name)
                    console.print("2. npm install")
                    console.print("3. Update .env.local with your Supabase credentials")
                    console.print("4. npm run dev")
                    
                except subprocess.CalledProcessError as e:
                    status.stop()
                    console.print("[red]Error: Failed to clone boilerplate repository[/red]")
                    raise typer.Exit(1)
        else:
            console.print("\n[yellow]Project creation cancelled.[/yellow]")
            
    except Exception as e:
        console.print(f"\n[red]Error generating specification: {str(e)}[/red]")
        raise typer.Exit(1)

def run():
    app() 