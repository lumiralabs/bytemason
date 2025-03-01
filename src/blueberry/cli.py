import typer
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
import subprocess
from blueberry.agents import ProjectBuilder, CodeAgent, SupabaseSetupAgent
from blueberry.models import ProjectSpec
import asyncio
import os
from pathlib import Path
import json
from datetime import datetime
import sys
import rich.box
import re
import shutil

# Terminal symbols with graceful fallback for non-Unicode terminals
SYMBOLS = {
    "success": "✓" if sys.stdout.encoding.lower() == "utf-8" else "SUCCESS",
    "error": "✗" if sys.stdout.encoding.lower() == "utf-8" else "ERROR",
    "warning": "!" if sys.stdout.encoding.lower() == "utf-8" else "WARNING",
    "info": "ℹ" if sys.stdout.encoding.lower() == "utf-8" else "INFO",
    "pending": "⋯" if sys.stdout.encoding.lower() == "utf-8" else "...",
}


def should_use_color(stream=sys.stdout) -> bool:
    """
    Determine if we should use color based on environment and stream capabilities.
    
    Checks:
    1. Terminal capability (TTY)
    2. Environment preferences (NO_COLOR, TERM)
    3. Unicode support
    """
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False

    if os.getenv("BERRY_NO_COLOR") or os.getenv("NO_COLOR"):
        return False
        
    if os.getenv("TERM") in ["dumb", None]:
        return False

    return stream.encoding and stream.encoding.lower() in ["utf-8", "utf8"]


def get_symbol(name: str) -> str:
    """Get the appropriate symbol based on terminal capabilities"""
    return SYMBOLS.get(name, "")


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
🚀 Blueberry CLI - AI-powered Next.js App Generator

Generate production-ready Next.js applications with AI assistance.
Blueberry helps you plan, build, and deploy full-stack apps from natural language descriptions.

Features:
• Next.js 14 with App Router
• Supabase Authentication & Database
• Modern UI Components
• API Routes & Data Models
• Production-ready Configuration

Documentation: https://lumiralabs.github.io/blueberry/
Issues: https://github.com/lumiralabs/blueberry/issues
""",
    no_args_is_help=True,
    add_completion=True,
)

# Initialize consoles with proper color detection
stdout_color = should_use_color(sys.stdout)
stderr_color = should_use_color(sys.stderr)

console = Console(
    force_terminal=stdout_color,
    emoji=stdout_color,
    highlight=stdout_color,
)
error_console = Console(
    stderr=True,
    force_terminal=stderr_color,
    emoji=stderr_color,
    highlight=stderr_color,
)


def create_progress(description: str = "") -> Progress:
    """Create a progress display with consistent styling"""
    if stdout_color:
        return Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
            refresh_per_second=10,
        )
    else:
        return Progress(
            TextColumn("{task.description}"),
            console=console,
            transient=False,
            expand=False,
        )


def display_features(features: List[str]):
    """Display features in a visually appealing way"""
    if not features:
        console.print("[yellow]No features specified[/yellow]")
        return
        
    feature_panels = [
        Panel(f" {feature}", expand=True, border_style="blue")
        for feature in features
    ]
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
            component.name, component.description, "\n".join(component.dependencies)
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
            "Required" if route.auth_required else "Public",
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


@app.command()
def create(
    prompt: str = typer.Argument(
        None,
        help="Natural language description of your app",
        show_default=False,
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version information",
        rich_help_panel="Utility",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output",
        rich_help_panel="Utility",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q", 
        help="Minimize output",
        rich_help_panel="Utility",
    ),
):
    """
    Generate a Next.js application from a natural language description.

    Your description should include the core functionality and features you want.
    Blueberry will analyze your requirements and generate a complete application.

    Features:
    • Next.js 14 frontend with modern UI
    • Supabase backend with auth
    • API routes and data models
    • Production deployment config

    Examples:
        $ berry create "Todo list app with user authentication"
        $ berry create "Blog with markdown and comments"
        $ berry create "Chat app with real-time messages"
    """
    if no_color:
        console.force_terminal = False
        console.emoji = False
        console.highlight = False
        error_console.force_terminal = False
        error_console.emoji = False
        error_console.highlight = False

    if version:
        try:
            from importlib.metadata import version as get_version
            v = get_version("blueberry")
            console.print(f"Blueberry v{v}")
        except:
            console.print("Version information not available")
        raise typer.Exit()

    if not prompt:
        error_console.print(
            format_message("error", "Please provide a description of your app")
        )
        if not quiet:
            console.print("\nExample:")
            console.print('  berry create "Todo list app with authentication"')
            console.print("\nFor more help:")
            console.print("  berry create --help")
        raise typer.Exit(1)

    try:
        asyncio.run(generate_app(prompt, quiet))
    except KeyboardInterrupt:
        error_console.print("\n" + format_message("warning", "Operation cancelled"))
        raise typer.Exit(130)
    except Exception as e:
        error_console.print("\n" + format_message("error", f"Error: {str(e)}"))
        if not quiet:
            console.print("\nFor help:")
            console.print("  berry create --help")
        raise typer.Exit(1)


async def generate_app(prompt: str, quiet: bool = False):
    """Generate application from prompt"""
    builder = ProjectBuilder()

    # Analyze requirements
    with create_progress() as progress:
        task = progress.add_task("📝 Analyzing requirements...")
        try:
            intent = builder.understand_intent(prompt)
            progress.update(task, completed=True)
        except Exception as e:
            raise Exception(f"Failed to analyze requirements: {str(e)}")

    # if not quiet:
    #     console.print("\n" + format_message("info", "Planned features:"))
    #     display_features(intent.features)

    # Generate specification
    with create_progress() as progress:
        task = progress.add_task("🔨 Generating specification...")
        try:
            spec = builder.create_spec(intent)
            progress.update(task, completed=True)
        except Exception as e:
            raise Exception(f"Failed to generate specification: {str(e)}")

    console.print("\n" + format_message("success", "Specification ready!"))

    try:
        project_name = spec.name.lower().replace(" ", "-")

        # Clone template
        with create_progress() as progress:
            task = progress.add_task("📦 Preparing project...")
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth=1",
                        "--quiet",
                        "https://github.com/iminoaru/boilerplate.git",
                        project_name,
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                progress.update(task, completed=True)
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to clone template: {e.stderr}")

        project_path = os.path.abspath(project_name)
        if not quiet:
            console.print(
                format_message("info", f"Project location: [bold]{project_path}[/bold]")
            )

        # Setup project
        original_dir = os.getcwd()
        os.chdir(project_path)

        try:
            # Setup Supabase
            if not quiet:
                console.print("\n" + format_message("info", "Configuring Supabase..."))
            if not builder.setup_supabase(spec):
                raise Exception("Supabase setup failed")

            # Generate code
            with create_progress() as progress:
                task = progress.add_task("🚀 Generating application...")
                code_agent = CodeAgent(project_path, spec)
                success = await code_agent.transform_template()
                if not success:
                    raise Exception("Code generation failed")
                progress.update(task, completed=True)

            # Success!
            console.print("\n" + format_message("success", "Project ready!"))

            if not quiet:
                console.print("\n" + format_message("info", "Next steps:"))
                console.print(f"  1. cd {project_name}")
                console.print("  2. npm install")
                console.print("  3. npm run dev")

        finally:
            os.chdir(original_dir)

    except Exception as e:
        # Cleanup on failure
        shutil.rmtree(project_name, ignore_errors=True)
        raise e


def get_project_status():
    """Get the current status of projects in the workspace"""
    specs_dir = Path("specs")
    status = {"specs": [], "projects": [], "last_generated": None}

    # Check for spec files
    if specs_dir.exists():
        for spec_file in specs_dir.glob("*_spec.json"):
            try:
                with open(spec_file) as f:
                    spec = json.load(f)
                status["specs"].append(
                    {
                        "name": spec["name"],
                        "file": spec_file.name,
                        "features": len(spec["features"]),
                        "modified": datetime.fromtimestamp(
                            spec_file.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
            except:
                continue

    # Check for generated projects
    for item in Path().iterdir():
        if (
            item.is_dir()
            and not item.name.startswith(".")
            and item.name not in ["specs", "src"]
        ):
            supabase_dir = item / "supabase"
            next_config = item / "next.config.js"
            if supabase_dir.exists() and next_config.exists():
                status["projects"].append(
                    {
                        "name": item.name,
                        "path": str(item.absolute()),
                        "has_migrations": any(
                            (supabase_dir / "migrations").glob("*.sql")
                        )
                        if (supabase_dir / "migrations").exists()
                        else False,
                        "modified": datetime.fromtimestamp(
                            item.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

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
            show_header=True, box=rich.box.SIMPLE if stdout_color else None
        )
        spec_table.add_column("Name", style="cyan")
        spec_table.add_column("File", style="dim")
        spec_table.add_column("Features", justify="right")
        spec_table.add_column("Last Modified", style="green")

        for spec in status["specs"]:
            spec_table.add_row(
                spec["name"], spec["file"], str(spec["features"]), spec["modified"]
            )
        console.print(spec_table)
    else:
        console.print(
            format_message(
                "warning", "[yellow]No project specifications found.[/yellow]"
            )
        )
        console.print("To create one, run:")
        console.print('  berry create "describe your app"')

    # Generated Projects
    console.print(format_message("info", "🚀 Generated Projects"))
    if status["projects"]:
        project_table = Table(
            show_header=True, box=rich.box.SIMPLE if stdout_color else None
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
                project["modified"],
            )
        console.print(project_table)
    else:
        console.print(
            format_message("warning", "[yellow]No generated projects found.[/yellow]")
        )

    # Next Steps
    console.print(format_message("info", "📝 Available Actions"))
    actions = Tree("Actions")

    if not status["specs"]:
        actions.add("Generate a new project specification:")
        actions.add('  berry create "describe your app"')
    elif not status["projects"]:
        actions.add("Generate a project from existing specification:")
        for spec in status["specs"]:
            actions.add(f'  berry create "Use specification from {spec["file"]}"')
    else:
        for project in status["projects"]:
            project_actions = actions.add(f"[cyan]{project['name']}[/cyan]")
            project_actions.add("Start development server:")
            project_actions.add(f"  cd {project['name']} && npm run dev")
            if not project["has_migrations"]:
                project_actions.add("Set up database:")
                project_actions.add(f"  cd {project['name']} && npx supabase init")

    console.print(actions)


@app.command(name="plan")
def plan(
    prompt: str = typer.Argument(
        ...,
        help="Natural language description of your app",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file name (default: name_timestamp_spec.json)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimize output",
    ),
):
    """
    Plan your application from a description.

    Creates a detailed project plan including:
    • Project structure
    • Database schema
    • API routes
    • UI components
    • Authentication setup

    The plan can be used to:
    1. Generate code (berry generate)
    2. Create database schema (berry db generate)
    3. Track project evolution

    Examples:
        $ berry plan "Todo list with user authentication"
        $ berry plan "Blog with comments" -o blog_spec.json
    """
    try:
        builder = ProjectBuilder()

        # Clean project name
        project_name = os.path.basename(os.getcwd()).lower().replace(" ", "-")

        # Analyze requirements
        with create_progress() as progress:
            task = progress.add_task("📝 Analyzing requirements...")
            intent = builder.understand_intent(prompt)
            progress.update(task, completed=True)

        # Display features
        # if not quiet:
        #     console.print("\n" + format_message("info", "Planned features:"))
        #     display_features(intent.features)

        # Generate specification
        with create_progress() as progress:
            task = progress.add_task("🔨 Generating specification...")
            spec = builder.create_spec(intent)
            spec.name = project_name
            progress.update(task, completed=True)

        # Create specs directory
        specs_dir = Path("specs")
        specs_dir.mkdir(exist_ok=True)

        # Generate filename
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"{spec.name}_{timestamp}_spec.json"

        spec_file = specs_dir / output
        
        # Save specification
        with open(spec_file, "w") as f:
            json.dump(spec.dict(), f, indent=2)

        console.print("\n" + format_message("success", f"Specification saved: {spec_file}"))

        if not quiet:
            console.print("\n" + format_message("info", "Next steps:"))
            console.print("  1. Review the specification")
            console.print("  2. berry db setup  # Configure database")
            console.print(f"  3. berry db generate {spec_file}  # Generate database schema")
            console.print(f"  4. berry db push {spec_file}  # Apply schema to database")
            console.print(f"  5. berry code {spec_file}  # Generate code")
    except Exception as e:
        error_console.print("\n" + format_message("error", f"Error: {str(e)}"))
        raise typer.Exit(1)


# Create a subgroup for database commands
db = typer.Typer(
    name="db",
    help="Manage database and authentication setup",
    no_args_is_help=True,
)

# Register the database group with the main app
app.add_typer(db)

@db.command()
def setup(
    spec_file: str = typer.Argument(
        None,
        help="Path to specification file (optional)",
    ),
    url: str = typer.Option(
        None,
        "--url",
        "-u",
        help="Supabase project URL (e.g., https://xxx.supabase.co)",
        prompt="Project URL",
    ),
    anon_key: str = typer.Option(
        None,
        "--anon-key",
        "-k",
        help="Supabase anon key",
        prompt="Anon key",
    ),
    service_key: str = typer.Option(
        None,
        "--service-key",
        "-s",
        help="Supabase service role key",
        prompt="Service role key",
        hide_input=True,
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file name for schema (default: timestamp_schema.sql)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimize output",
    ),
):
    """
    Configure database connection and generate schema.

    Sets up your project with Supabase credentials and optionally 
    generates database schema from specification.

    The setup process will:
    1. Configure environment variables for Supabase
    2. Initialize local development
    3. Link to your Supabase project
    4. Generate database schema (if spec file provided)

    Examples:
        $ berry db setup                          # Basic setup
        $ berry db setup specs/myapp_spec.json    # Setup + schema generation
    """
    try:
        # Extract project ref from URL
        if "supabase.co" in url:
            project_ref = url.split("//")[1].split(".")[0]
        else:
            project_ref = url
            url = f"https://{project_ref}.supabase.co"

        # Validate project ref format
        if not project_ref.isalnum() or len(project_ref) != 20:
            raise ValueError(
                "Invalid project reference. Must be a 20-character alphanumeric string."
            )

        # Create agent and setup environment
        spec = None
        if spec_file:
            # Load and validate spec if provided
            with open(spec_file) as f:
                spec_data = json.load(f)
            spec = ProjectSpec(**spec_data)
            
        agent = SupabaseSetupAgent(spec, os.getcwd())
        
        # Set up environment variables
        if not quiet:
            console.print(format_message("info", "Setting up environment..."))
        agent.setup_environment(project_ref, anon_key, service_key)

        # Initialize project
        if not quiet:
            console.print(format_message("info", "Initializing database..."))
        agent.initialize_project(project_ref)
        
        console.print(format_message("success", "Database setup complete!"))
        
        # Generate schema if spec is provided
        if spec:
            if not quiet:
                console.print("\n" + format_message("info", "Generating schema..."))
            
            migration_sql = agent.get_migration_sql()
            
            # Create migrations directory
            migrations_dir = Path("supabase/migrations")
            migrations_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            if not output:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output = f"{timestamp}_schema.sql"
            
            migration_file = migrations_dir / output
            
            with open(migration_file, "w") as f:
                f.write(migration_sql)
            
            console.print(
                format_message("success", f"Generated schema: {migration_file}")
            )
            
            if not quiet:
                console.print("\n" + format_message("info", "Next step:"))
                console.print("  berry db push  # Apply schema to database")
        else:
            if not quiet:
                console.print("\n" + format_message("info", "Next steps:"))
                console.print("  1. berry plan \"Your app description\"  # Plan your app")
                console.print("  2. berry db setup specs/yourapp_spec.json  # Generate schema")
                console.print("  3. berry db push  # Apply schema to database")

    except Exception as e:
        error_console.print("\n" + format_message("error", f"Setup failed: {str(e)}"))
        # Clean up if something went wrong
        if os.path.exists(".env.local"):
            os.remove(".env.local")
        raise typer.Exit(1)


# @db.command()
# def generate(
#     spec_file: str = typer.Argument(
#         ...,
#         help="Path to specification file",
#     ),
#     output: str = typer.Option(
#         None,
#         "--output",
#         "-o",
#         help="Output file name (default: timestamp_schema.sql)",
#     ),
#     quiet: bool = typer.Option(
#         False,
#         "--quiet",
#         "-q",
#         help="Minimize output",
#     ),
# ):
#     """
#     Generate database schema from specification.

#     Creates SQL migration files that define:
#     • Database tables
#     • Relationships
#     • Indexes
#     • Security policies

#     The generated schema will be saved in:
#     supabase/migrations/

#     Examples:
#         $ berry db generate specs/myapp_spec.json
#         $ berry db generate specs/myapp_spec.json -o initial.sql
#     """
#     console.print(format_message("warning", "This command is deprecated. Use 'berry db setup' instead."))
#     try:
#         # Load and validate spec
#         with open(spec_file) as f:
#             spec_data = json.load(f)
#         spec = ProjectSpec(**spec_data)

#         # Create agent
#         agent = SupabaseSetupAgent(spec, os.getcwd())
        
#         if not quiet:
#             console.print(format_message("info", "Generating schema..."))
        
#         migration_sql = agent.get_migration_sql()
        
#         # Create migrations directory
#         migrations_dir = Path("supabase/migrations")
#         migrations_dir.mkdir(parents=True, exist_ok=True)

#         # Generate filename
#         if not output:
#             timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#             output = f"{timestamp}_schema.sql"
        
#         migration_file = migrations_dir / output
        
#         with open(migration_file, "w") as f:
#             f.write(migration_sql)
        
#         console.print(
#             format_message("success", f"Generated schema: {migration_file}")
#         )

#         if not quiet:
#             console.print("\n" + format_message("info", "Next step:"))
#             console.print("  berry db push  # Apply schema to database")

#     except Exception as e:
#         error_console.print(
#             format_message("error", f"Schema generation failed: {str(e)}")
#         )
#         raise typer.Exit(1)


@db.command()
def push(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show changes without applying them",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimize output",
    ),
):
    """
    Apply schema changes to the database.

    Pushes local migrations to your Supabase database:
    • Applies new migrations
    • Updates tables and relationships
    • Maintains data integrity
    • Shows detailed change log

    Migrations are applied from:
    supabase/migrations/

    Examples:
        $ berry db push
        $ berry db push --dry-run  # Preview changes
        $ berry db push --force    # Skip confirmation
    """
    try:
        # Check for environment variables
        env_file = Path(".env.local")
        if not env_file.exists():
            raise Exception(
                "Environment not configured. Run 'berry db setup' first"
            )

        # Check for migrations
        migrations_dir = Path("supabase/migrations")
        if not migrations_dir.exists() or not any(migrations_dir.glob("*.sql")):
            raise Exception(
                "No migrations found. Run 'berry db generate' first"
            )

        # Add --dry-run flag if requested
        cmd = ["npx", "supabase", "db", "push"]
        if dry_run:
            cmd.append("--dry-run")
        if force:
            cmd.append("--force")
            
        if not quiet:
            console.print(format_message("info", "Applying schema changes..."))
        
        # Run command without capturing output to allow password prompt
        try:
            subprocess.run(cmd, check=True)
            console.print(format_message("success", "Schema updated successfully"))
            
            if not quiet:
                console.print("\n" + format_message("info", "Next steps:"))
                console.print("  1. npm run dev  # Start development")
                console.print("  2. Check Supabase dashboard for changes")
        except subprocess.CalledProcessError as e:
            raise Exception("Failed to apply schema changes")

    except Exception as e:
        error_console.print(format_message("error", f"Error: {str(e)}"))
        raise typer.Exit(1)


@app.command()
def code(
    spec_file: str = typer.Argument(
        ...,
        help="Path to the specification file",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimize output",
    ),
):
    """
    Generate code from your project plan.

    Takes your project plan and generates:
    • Next.js components and pages
    • API routes and handlers
    • Database models and types
    • Authentication flows
    • UI components

    The code is generated in the current directory.
    Existing node_modules are preserved.

    Examples:
        $ berry code specs/myapp_spec.json
        $ berry code path/to/spec.json --quiet
    """
    try:
        # Load and validate spec
        with open(spec_file) as f:
            spec_data = json.load(f)
        spec = ProjectSpec(**spec_data)

        project_path = os.getcwd()
        
        # Check if we're not inside node_modules
        if "node_modules" in project_path:
            raise ValueError("Cannot run code inside node_modules")
            
        if not quiet:
            console.print(
                format_message("info", f"Project location: [bold]{project_path}[/bold]")
            )

        # Generate code
        with create_progress() as progress:
            task = progress.add_task("🚀 Generating application code...")
            code_agent = CodeAgent(project_path, spec, ignore_patterns=["node_modules/**"])
            success = asyncio.run(code_agent.transform_template())
            if not success:
                raise Exception("Code generation failed")
            progress.update(task, completed=True)

        console.print("\n" + format_message("success", "Code generated successfully!"))

        if not quiet:
            console.print("\n" + format_message("info", "Next steps:"))
            console.print("  1. npm install")
            console.print("  2. berry db setup")
            console.print("  3. npm run dev")

    except Exception as e:
        error_console.print("\n" + format_message("error", f"Error: {str(e)}"))
        raise typer.Exit(1)


@app.command()
def new(
    project_name: str = typer.Argument(
        ...,
        help="Name of the new project",
    ),
    template: str = typer.Option(
        "default",
        "--template",
        "-t",
        help="Template to use",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimize output",
    ),
):
    """
    Create a new project from scratch.

    Sets up a new Next.js + Supabase project with:
    • Modern project structure
    • Authentication ready
    • API routes configured
    • Development environment

    Examples:
        $ berry new my-app
        $ berry new my-blog --template blog
    """
    try:
        # Validate name
        if not re.match(r"^[a-z0-9-]+$", project_name):
            raise ValueError(
                "Project name can only contain lowercase letters, numbers, and hyphens"
            )

        if Path(project_name).exists():
            raise ValueError(f"Directory '{project_name}' already exists")

        with create_progress() as progress:
            # Clone template
            task = progress.add_task("📦 Creating project...")
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth=1",
                        "--quiet",
                        "https://github.com/iminoaru/boilerplate.git",
                        project_name,
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                raise ValueError(f"Failed to clone template: {e.stderr}")

            progress.update(task, completed=True)

            # Setup git
            task = progress.add_task("🔧 Configuring project...")
            shutil.rmtree(Path(project_name) / ".git", ignore_errors=True)

            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=project_name,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            subprocess.run(
                ["git", "add", "."],
                cwd=project_name,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            subprocess.run(
                ["git", "commit", "-m", "Initial commit", "--quiet"],
                cwd=project_name,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            progress.update(task, completed=True)

        console.print("\n" + format_message("success", f"Created project {project_name}"))

        if not quiet:
            console.print("\n" + format_message("info", "Next steps:"))
            console.print(f"  1. cd {project_name}")
            console.print("  2. npm install")
            console.print('  3. berry plan "Your app description"  # Plan your app')
            console.print("  4. berry db setup  # Configure database")
            console.print("  5. npm run dev  # Start development")

    except Exception as e:
        error_console.print("\n" + format_message("error", f"Error: {str(e)}"))
        # Cleanup
        if "project_name" in locals():
            shutil.rmtree(project_name, ignore_errors=True)
        raise typer.Exit(1)


@app.command()
def repair(
    spec_file: str = typer.Option(
        None,
        "--spec",
        "-s",
        help="Path to specification file",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Minimize output",
    ),
):
    """
    Repair and fix build errors in generated code.

    Analyzes the current build errors and attempts to fix them using AI.
    Can work with or without a specification file.

    Examples:
        $ berry repair
        $ berry repair --spec specs/myapp_spec.json
    """
    try:
        # Load spec if provided
        spec = None
        if spec_file:
            with open(spec_file) as f:
                spec_data = json.load(f)
                spec = ProjectSpec(**spec_data)

        # Create code agent with node_modules ignored
        code_agent = CodeAgent(os.getcwd(), spec, ignore_patterns=["node_modules/**"])

        # Run build and get errors
        with create_progress() as progress:
            task = progress.add_task("[cyan]Checking build...", total=None)
            errors = asyncio.run(code_agent._run_build())
            progress.update(task, completed=True)

        if not errors:
            console.print(format_message("success", "No build errors found!"))
            return

        # Show errors
        if not quiet:
            console.print(format_message("warning", f"Found {len(errors)} build errors:"))
            for error in errors:
                console.print(f"  • [red]{error.file}:[/red] {error.message}")

        # Confirm repair
        if not quiet and not typer.confirm("\nAttempt to repair?", default=True):
            return

        # Run repair
        with create_progress() as progress:
            task = progress.add_task("[cyan]Repairing code...", total=None)
            asyncio.run(code_agent._repair_code(errors))
            progress.update(task, completed=True)

        # Final build check
        with create_progress() as progress:
            task = progress.add_task("[cyan]Verifying repairs...", total=None)
            remaining_errors = asyncio.run(code_agent._run_build())
            progress.update(task, completed=True)

        if remaining_errors:
            console.print(format_message("warning", f"{len(remaining_errors)} errors remain"))
            if not quiet:
                console.print("\nTry:")
                console.print("  1. Manual code review")
                console.print("  2. Run 'berry repair' again")
        else:
            console.print(format_message("success", "All errors fixed!"))

    except Exception as e:
        error_console.print(format_message("error", f"Repair failed: {str(e)}"))
        if not quiet:
            console.print("\nFor help:")
            console.print("  berry repair --help")
        raise typer.Exit(1)


def run():
    """Entry point for the CLI"""
    try:
        app()
    except Exception as e:
        error_console.print("\n" + format_message("error", f"Unexpected error: {str(e)}"))
        raise typer.Exit(1)
