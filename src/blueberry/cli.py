import typer
from typing import Optional, List
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
import subprocess
from blueberry.agents import ProjectBuilder, CodeAgent
from blueberry.models import ProjectSpec
import asyncio
import os
from pathlib import Path
import json
from datetime import datetime
import sys
import rich.box

# Symbols for different terminal capabilities
SYMBOLS = {
    "success": "✓" if sys.stdout.encoding.lower() == 'utf-8' else '+',
    "error": "❌" if sys.stdout.encoding.lower() == 'utf-8' else 'x',
    "warning": "⚠️" if sys.stdout.encoding.lower() == 'utf-8' else '!',
    "info": "ℹ️" if sys.stdout.encoding.lower() == 'utf-8' else 'i',
    "pending": "…" if sys.stdout.encoding.lower() == 'utf-8' else '...',
}

def should_use_color(stream=sys.stdout) -> bool:
    """
    Determine if we should use color based on environment and stream.
    Checks both stream capability and user preferences.
    """
    # Check if stream is a TTY
    if not hasattr(stream, 'isatty') or not stream.isatty():
        return False
    
    # Check environment variables (in order of precedence)
    if os.getenv('BERRY_NO_COLOR', ''):  # App-specific override
        return False
    if os.getenv('NO_COLOR', ''):  # System-wide preference
        return False
    if os.getenv('TERM') == 'dumb':  # Terminal capability
        return False
    if not os.getenv('TERM'):  # No terminal type set
        return False
    
    # Check encoding supports Unicode
    if stream.encoding and stream.encoding.lower() not in ['utf-8', 'utf8']:
        return False
    
    return True

def get_symbol(name: str) -> str:
    """Get the appropriate symbol based on terminal capabilities"""
    return SYMBOLS.get(name, '')

def format_message(msg_type: str, message: str, use_color: bool = True) -> str:
    """Format a message with appropriate symbol and color"""
    symbol = get_symbol(msg_type)
    
    if not use_color:
        return f"{symbol} {message}"
    
    color_map = {
        "success": "green",
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "pending": "cyan"
    }
    
    return f"[{color_map.get(msg_type, '')}]{symbol} {message}[/]"

app = typer.Typer(
    name="berry",
    help="""
Blueberry CLI - AI-powered full-stack app generator

Generate full-stack Next.js applications with AI assistance. Blueberry helps you plan,
build, test and deploy your app with a simple natural language prompt.

Commands:
    create     Generate a new application from a description
    status     Show current workspace state

Examples:
    $ berry create "Create a todo list app with authentication"
    $ berry create "Build a blog with markdown support and comments"
    $ berry status  # Show current system state

Shell Completion:
    $ berry --install-completion  # Install tab completion for your shell
    $ berry --show-completion     # Show completion script

For more information and documentation:
    https://lumiralabs.github.io/blueberry/

Report issues at:
    https://github.com/lumiralabs/blueberry/issues
""",
    no_args_is_help=True,  # Show help when no arguments are provided
    add_completion=True,  # Enable shell completion
)

# Initialize consoles with proper color detection
stdout_color = should_use_color(sys.stdout)
stderr_color = should_use_color(sys.stderr)

console = Console(
    force_terminal=stdout_color,
    emoji=stdout_color,  # Only use emoji when color is enabled
    highlight=stdout_color  # Only use syntax highlighting when color is enabled
)
error_console = Console(
    stderr=True,
    force_terminal=stderr_color,
    emoji=stderr_color,
    highlight=stderr_color
)

def create_progress() -> Progress:
    """Create a simple progress display based on environment"""
    if stdout_color:
        return Progress(
            SpinnerColumn(spinner_name="dots"),  # Simple dots spinner
            TextColumn("[bold]{task.description}"),  # Bold text, no fancy formatting
            console=console,
            transient=True,  # Clear spinner after completion
            refresh_per_second=8  # Slower refresh rate for stability
        )
    else:
        # Even simpler display for non-TTY environments
        return Progress(
            TextColumn("{task.description}"),
            console=console,
            transient=False,
            expand=False
        )

def display_features(features: List[str]):
    """Display features in a nice formatted way"""
    feature_panels = [Panel(f" {feature}", expand=True) for feature in features]
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

@app.command(name="create")
def main(
    code: Optional[str] = typer.Argument(
        None,
        help="Natural language prompt describing the app you want to build",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the application version",
        rich_help_panel="Utility Options"
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output and emoji",
        rich_help_panel="Utility Options"
    ),
    install_completion: bool = typer.Option(
        None,
        help="Install completion for the current shell",
        rich_help_panel="Shell Completion",
        callback=lambda: None,
    ),
    show_completion: bool = typer.Option(
        None,
        help="Show completion script for the current shell",
        rich_help_panel="Shell Completion",
        callback=lambda: None,
    )
):
    """
    Generate a full-stack Next.js application from a natural language prompt.
    
    The prompt should describe the core functionality and features you want in your app.
    Blueberry will analyze your requirements and generate a complete application with:
    
    - Next.js 14 frontend with modern UI components
    - Supabase backend with authentication and database
    - API routes and data models
    - Deployment configuration

    Examples:
        $ berry create "Create a todo list app with authentication"
        $ berry create "Build a blog with markdown support and comments"
        $ berry create "Make a real-time chat application with user profiles"
    """
    # Update color settings if --no-color is passed
    if no_color:
        console.force_terminal = False
        console.emoji = False
        console.highlight = False
        error_console.force_terminal = False
        error_console.emoji = False
        error_console.highlight = False

    if version:
        from importlib.metadata import version as get_version
        try:
            v = get_version("blueberry")
            console.print(f"Blueberry CLI version: {v}")
        except:
            console.print("Version information not available")
        raise typer.Exit()

    asyncio.run(async_main(code))

async def async_main(code: Optional[str]):
    """
    Async main function to handle coroutines
    """
    if not code:
        error_console.print(format_message("error", "No prompt provided. Please provide a description of your app."))
        console.print("\nExample:")
        console.print("  berry create \"Create a todo list app with authentication\"")
        console.print("\nFor more help:")
        console.print("  berry --help")
        raise typer.Exit(1)

    # Get project name from user with default
    project_name = Prompt.ask(
        format_message("info", "What would you like to name your project? (Press Enter to use default)"),
        default="my-app",
        show_default=True
    ).lower().replace(' ', '-')

    try:
        builder = ProjectBuilder()
        
        # Step 1: Understand Intent
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[bold]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Analyzing requirements...")
            intent = builder.understand_intent(code)
            progress.update(task, completed=True)
        
        # Display features
        console.print("\n" + format_message("info", "Based on your prompt, we'll build the following features:"))
        if stdout_color:
            display_features(intent.features)
        else:
            for feature in intent.features:
                console.print(f"- {feature}")
        
        # Step 2: Verify features with user
        if not typer.confirm("\nWould you like to modify these features?", default=False):
            console.print(format_message("success", "Using features as shown above"))
        else:
            intent = builder.verify_with_user_loop(intent)
        
        # Step 3: Generate Specification
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[bold]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Generating specification...")
            spec = builder.create_spec(intent)
            progress.update(task, completed=True)
        
        console.print("\n" + format_message("success", "Specification generated successfully!"))
        
        # Ask user to proceed
        if typer.confirm("\nWould you like to proceed with creating the project?", default=True):
            try:
                # Step 4: Clone boilerplate
                with Progress(
                    SpinnerColumn(spinner_name="dots"),
                    TextColumn("[bold]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("Cloning template...")
                    subprocess.run(
                        ['git', 'clone', 'https://github.com/iminoaru/boilerplate.git', project_name],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    progress.update(task, completed=True)
                
                # Setup project
                project_path = os.path.abspath(project_name)
                console.print(format_message("info", f"\nProject path: [bold]{project_path}[/bold]"))
                
                original_dir = os.getcwd()
                os.chdir(project_path)
                
                try:
                    # Step 5: Set up Supabase
                    console.print("\n" + format_message("info", "Setting up Supabase..."))
                    if not builder.setup_supabase(spec):
                        raise Exception("Supabase setup failed")
                    
                    # Step 6: Transform template
                    with Progress(
                        SpinnerColumn(spinner_name="dots"),
                        TextColumn("[bold]{task.description}"),
                        console=console,
                        transient=True
                    ) as progress:
                        task = progress.add_task("Generating application code...")
                        code_agent = CodeAgent(project_path, spec)
                        await code_agent.transform_template()
                        progress.update(task, completed=True)
                    
                    # Success!
                    console.print("\n" + format_message("success", "Project created successfully!"))
                    
                    # Show next steps
                    console.print("\n" + format_message("info", "Next steps:"))
                    console.print(f"  1. cd {project_name}")
                    console.print("  2. npm install")
                    console.print("  3. npm run dev")
                    
                finally:
                    os.chdir(original_dir)
                    
            except subprocess.CalledProcessError:
                raise Exception("Failed to clone boilerplate repository")
        else:
            console.print("\n" + format_message("info", "Project creation cancelled."))
            
    except Exception as e:
        error_console.print("\n" + format_message("error", f"Error: {str(e)}"))
        raise typer.Exit(1)

def get_project_status():
    """Get the current status of projects in the workspace"""
    specs_dir = Path("specs")
    status = {
        "specs": [],
        "projects": [],
        "last_generated": None
    }
    
    # Check for spec files
    if specs_dir.exists():
        for spec_file in specs_dir.glob("*_spec.json"):
            try:
                with open(spec_file) as f:
                    spec = json.load(f)
                status["specs"].append({
                    "name": spec["name"],
                    "file": spec_file.name,
                    "features": len(spec["features"]),
                    "modified": datetime.fromtimestamp(spec_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except:
                continue
    
    # Check for generated projects
    for item in Path().iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name in ['specs', 'src']:
            supabase_dir = item / "supabase"
            next_config = item / "next.config.js"
            if supabase_dir.exists() and next_config.exists():
                status["projects"].append({
                    "name": item.name,
                    "path": str(item.absolute()),
                    "has_migrations": any((supabase_dir / "migrations").glob("*.sql")) if (supabase_dir / "migrations").exists() else False,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
    
    return status

@app.command()
def status():
    """
    Show the current state of the Blueberry workspace
    
    This includes:
    - Available project specifications
    - Generated projects and their status
    - Next steps and available actions
    """
    status = get_project_status()
    
    # Project Specifications
    console.print(format_message("info", "Project Specifications"))
    if status["specs"]:
        spec_table = Table(
            show_header=True,
            box=rich.box.SIMPLE if stdout_color else None
        )
        spec_table.add_column("Name", style="cyan")
        spec_table.add_column("File", style="dim")
        spec_table.add_column("Features", justify="right")
        spec_table.add_column("Last Modified", style="green")
        
        for spec in status["specs"]:
            spec_table.add_row(
                spec["name"],
                spec["file"],
                str(spec["features"]),
                spec["modified"]
            )
        console.print(spec_table)
    else:
        console.print(format_message("warning", "[yellow]No project specifications found.[/yellow]"))
        console.print("To create one, run:")
        console.print("  berry create \"describe your app\"")
    
    # Generated Projects
    console.print(format_message("info", "🚀 Generated Projects"))
    if status["projects"]:
        project_table = Table(
            show_header=True,
            box=rich.box.SIMPLE if stdout_color else None
        )
        project_table.add_column("Name", style="cyan")
        project_table.add_column("Path", style="dim")
        project_table.add_column("Migrations", justify="center")
        project_table.add_column("Last Modified", style="green")
        
        for project in status["projects"]:
            project_table.add_row(
                project["name"],
                project["path"],
                "✓" if project["has_migrations"] else "✗",
                project["modified"]
            )
        console.print(project_table)
    else:
        console.print(format_message("warning", "[yellow]No generated projects found.[/yellow]"))
    
    # Next Steps
    console.print(format_message("info", "📝 Available Actions"))
    actions = Tree("Actions")
    
    if not status["specs"]:
        actions.add("Generate a new project specification:")
        actions.add("  berry create \"describe your app\"")
    elif not status["projects"]:
        actions.add("Generate a project from existing specification:")
        for spec in status["specs"]:
            actions.add(f"  berry create \"Use specification from {spec['file']}\"")
    else:
        for project in status["projects"]:
            project_actions = actions.add(f"[cyan]{project['name']}[/cyan]")
            project_actions.add("Start development server:")
            project_actions.add(f"  cd {project['name']} && npm run dev")
            if not project["has_migrations"]:
                project_actions.add("Set up database:")
                project_actions.add(f"  cd {project['name']} && npx supabase init")
    
    console.print(actions)

def run():
    app() 