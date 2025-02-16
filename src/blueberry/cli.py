import typer
from typing import Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from blueberry.agents import MasterAgent, CodeGeneratorAgent
from blueberry.models import ProjectSpec
import json
import os
from pathlib import Path

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
    overview.add_row("[bold]Name:[/bold]", spec.project.name)
    overview.add_row("[bold]Description:[/bold]", spec.project.description)
    overview.add_row("[bold]Tech Stack:[/bold]", ", ".join(spec.project.techStack))
    console.print(Panel(overview, title="Project Overview", border_style="blue"))
    
    # Frontend Structure
    frontend_table = Table(show_header=True)
    frontend_table.add_column("Page", style="cyan")
    frontend_table.add_column("Type", style="green")
    frontend_table.add_column("Components", style="white")
    frontend_table.add_column("Auth", style="yellow")
    
    for path, page in spec.frontendStructure.pages.items():
        auth_info = "Required" if page.authRequired else "Public"
        if page.authRedirect:
            auth_info += f" (→ {page.authRedirect})"
        frontend_table.add_row(
            path,
            page.type,
            "\n".join(page.components),
            auth_info
        )
    console.print(Panel(frontend_table, title="Frontend Pages", border_style="cyan"))
    
    # Components
    components_table = Table(show_header=True)
    components_table.add_column("Category", style="cyan")
    components_table.add_column("Components", style="white")
    
    for category, components in spec.frontendStructure.components.items():
        components_table.add_row(category, "\n".join(components))
    console.print(Panel(components_table, title="Components", border_style="magenta"))
    
    # API Routes
    api_table = Table(show_header=True)
    api_table.add_column("Group", style="cyan")
    api_table.add_column("Endpoint", style="green")
    api_table.add_column("Method", style="yellow")
    api_table.add_column("Middleware", style="white")
    api_table.add_column("Supabase", style="magenta")
    
    for group, routes in spec.apiRoutes.items():
        for endpoint, config in routes.root.items():
            if isinstance(config, dict):
                for method, details in config.items():
                    api_table.add_row(
                        group,
                        endpoint,
                        method,
                        "\n".join(details.get("middleware", [])),
                        details.get("supabase", "")
                    )
            else:
                api_table.add_row(
                    group,
                    endpoint,
                    config.method or "",
                    "\n".join(config.middleware or []),
                    config.supabase
                )
    console.print(Panel(api_table, title="API Routes", border_style="green"))
    
    # Database Tables
    db_table = Table(show_header=True)
    db_table.add_column("Table", style="cyan")
    db_table.add_column("Columns", style="white")
    db_table.add_column("RLS Policies", style="yellow")
    
    for table, config in spec.supabaseConfig.tables.items():
        columns = "\n".join([f"{col}: {type}" for col, type in config.columns.items()])
        rls = "\n".join([f"{policy}: {rule}" for policy, rule in (config.RLS or {}).items()])
        db_table.add_row(table, columns, rls)
    
    console.print(Panel(db_table, title="Database Schema", border_style="yellow"))
    
    # Features
    features_table = Table(show_header=True)
    features_table.add_column("Category", style="cyan")
    features_table.add_column("Features", style="white")
    
    for category, features in spec.features.items():
        features_table.add_row(category, "\n".join([f"• {feature}" for feature in features]))
    console.print(Panel(features_table, title="Features", border_style="blue"))
    
    # Environment Variables
    env_table = Table(show_header=True)
    env_table.add_column("Variable", style="cyan")
    env_table.add_column("Type", style="white")
    
    for var, type in spec.environmentVariables.items():
        env_table.add_row(var, type)
    console.print(Panel(env_table, title="Environment Variables", border_style="green"))
    
    # Acceptance Criteria
    criteria_table = Table(show_header=False, box=None)
    for criterion in spec.acceptanceCriteria:
        criteria_table.add_row(f"✓ {criterion}")
    console.print(Panel(criteria_table, title="Acceptance Criteria", border_style="blue"))

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
    code: Optional[str] = typer.Option(None, "--code", help="The prompt to process"),
    output_dir: Optional[str] = typer.Option(".", "--output", "-o", help="Output directory for the generated codebase")
):
    """
    Blueberry CLI - Process code generation prompts
    """
    if not code:
        console.print("[red]Please provide a prompt using --code flag[/red]")
        raise typer.Exit()

    # Convert output_dir to Path
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    if not output_path.exists():
        try:
            output_path.mkdir(parents=True)
        except Exception as e:
            console.print(f"[red]Error creating output directory: {str(e)}[/red]")
            raise typer.Exit(1)
    elif not output_path.is_dir():
        console.print(f"[red]Output path {output_dir} exists but is not a directory[/red]")
        raise typer.Exit(1)
    elif any(output_path.iterdir()):
        if not Confirm.ask(f"\nOutput directory {output_dir} is not empty. Continue?"):
            raise typer.Exit()

    # Step 1: Understand Intent
    with console.status("[bold green]Understanding your requirements...") as status:
        agent = MasterAgent()
        intent = agent.understand_intent(code)
    
    # Display features
    console.print("\n[bold blue]Based on your prompt, we'll build the following features:[/bold blue]")
    display_features(intent.features)
    
    # Step 2: Verify and modify features with user
    intent = agent.verify_with_user_loop(intent)
    
    # Step 3: Get user preferences if they want to proceed
    if Confirm.ask("\nWould you like to customize the project preferences?"):
        preferences = get_user_preferences()
        intent.preferences = preferences
    
    # Step 4: Generate Specification
    try:
        with console.status("[bold green]Generating detailed specification...") as status:
            spec = agent.create_spec(intent)
            status.stop()
            
        console.print("\n[bold green]✨ Specification generated successfully![/bold green]")
        
        # Display the specification
        display_spec(spec)
        
        # Step 5: Generate codebase if user wants to proceed
        if Confirm.ask("\nWould you like to generate the codebase now?"):
            # Load scaffold configuration
            scaffold_path = Path(__file__).parent.parent.parent / "scaffold.json"
            if not scaffold_path.exists():
                console.print("[red]Error: scaffold.json not found[/red]")
                raise typer.Exit(1)
                
            with open(scaffold_path, "r") as f:
                scaffold_config = json.load(f)
            
            # Initialize code generator
            code_generator = CodeGeneratorAgent(spec, scaffold_config)
            
            # Generate codebase
            with console.status("[bold green]Generating codebase...") as status:
                result = code_generator.generate(str(output_path))
                status.stop()
            
            # Display generation summary
            console.print("\n[bold green]🎉 Codebase generated successfully![/bold green]")
            
            # Show summary of generated files
            files_table = Table(show_header=True)
            files_table.add_column("Type", style="cyan")
            files_table.add_column("Count", style="green")
            
            files_table.add_row("Files", str(len(result["files"])))
            files_table.add_row("API Routes", str(len(result["api_routes"])))
            files_table.add_row("Components", str(len(result["components"])))
            files_table.add_row("Migrations", str(len(result["migrations"])))
            files_table.add_row("Auth Components", str(len(result["auth_config"]["components"])))
            files_table.add_row("Environment Variables", str(len(result["env_vars"])))
            
            console.print(Panel(files_table, title="Generation Summary", border_style="green"))
            
            # Create .env file
            env_path = output_path / ".env"
            with open(env_path, "w") as f:
                for var, type in result["env_vars"].items():
                    f.write(f"{var}=\n")
            
            console.print(f"\n[yellow]Don't forget to fill in your environment variables in {env_path}[/yellow]")
            
            # Show next steps
            next_steps = [
                "1. Fill in the environment variables in .env",
                "2. Install dependencies with 'npm install'",
                "3. Run database migrations",
                "4. Start the development server with 'npm run dev'"
            ]
            
            console.print("\n[bold blue]Next steps:[/bold blue]")
            for step in next_steps:
                console.print(f"  • {step}")
            
        # Save spec to file if requested
        if Confirm.ask("\nWould you like to save the specification to a file?"):
            spec_file = output_path / f"{spec.project.name.lower().replace(' ', '-')}-spec.json"
            with open(spec_file, 'w') as f:
                f.write(spec.model_dump_json(indent=2))
            console.print(f"\n[green]Specification saved to {spec_file}[/green]")
            
    except Exception as e:
        console.print(f"\n[red]Error generating specification: {str(e)}[/red]")
        raise typer.Exit(1)

def run():
    app() 