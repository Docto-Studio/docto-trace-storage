"""
`docto-trace onboard` — unified guided wizard to set up everything for the first time.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from docto_trace.config import settings

console = Console()
err_console = Console(stderr=True)


def onboard() -> None:
    """
    Unified guided wizard to set up everything for the first time.
    """
    # ------------------------------------------------------------------
    # Step 0 - Lazy import commands to avoid crash if deps not installed
    # ------------------------------------------------------------------
    # We don't import them at top level anymore.
    
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]DOCTO TRACE — ONBOARDING[/bold cyan]\n"
            "[dim]Setting up your storage auditing environment in minutes.[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # ------------------------------------------------------------------
    # Step 1 — Environment Check (Virtual Env)
    # ------------------------------------------------------------------
    console.rule("[bold]Step 1 of 5 — Environment Check[/bold]")
    
    is_dev_mode = Path("pyproject.toml").exists()
    is_venv = sys.prefix != sys.base_prefix
    
    if is_dev_mode:
        console.print("[dim]Dev Mode detected (pyproject.toml found). Ensuring environment is ready...[/dim]")
        venv_dir = Path(".venv")
        
        # Path to venv's python executable
        if sys.platform == "win32":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"

        if not is_venv:
            console.print(
                "\n[yellow]⚠️  You are running from source but not in a virtual environment.[/yellow]\n"
            )
            if not venv_dir.exists():
                if Confirm.ask("  Create a local .venv/ for development?", default=True):
                    _run_command([sys.executable, "-m", "venv", str(venv_dir)])
                    console.print("\n[green]✅ Virtual environment created.[/green]")
            
            if venv_python.exists():
                if sys.platform == "win32":
                    venv_pip = venv_dir / "Scripts" / "pip.exe"
                    venv_bin = venv_dir / "Scripts" / "docto-trace.exe"
                else:
                    venv_pip = venv_dir / "bin" / "pip"
                    venv_bin = venv_dir / "bin" / "docto-trace"

                with console.status("[bold]🔧 Bootstrapping dev environment…[/bold]", spinner="dots"):
                    _run_command([str(venv_pip), "install", "-e", ".", "-q"])

                console.print(f"\n[bold green]🚀 Transitioning to dev venv...[/bold green]\n")
                os.execv(str(venv_bin), [str(venv_bin), "onboard"])
        else:
            console.print(f"\n[green]✅ Running in dev venv:[/green] [dim]{sys.prefix}[/dim]\n")
    else:
        # User Mode - Just check if we are in a venv (recommended but not forced)
        if is_venv:
            console.print(f"\n[green]✅ Running in virtual environment:[/green] [dim]{sys.prefix}[/dim]\n")
        else:
            console.print("\n[dim]Running in global python environment (not in a venv).[/dim]\n")

    # ------------------------------------------------------------------
    # Step 2 — Install Dependencies
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 2 of 5 — Dependencies & UI[/bold]")
    
    install_ui = Confirm.ask(
        "\n  Do you want to install the [bold]Interactive UI[/bold]? (requires streamlit/plotly)",
        default=True,
    )
    
    if install_ui:
        with console.status("[bold]📦 Installing UI extras…[/bold]", spinner="dots"):
            if is_dev_mode:
                _run_command([sys.executable, "-m", "pip", "install", "-e", ".[ui]", "-q"])
            else:
                # Global/User mode: install from PyPI
                _run_command([sys.executable, "-m", "pip", "install", "docto-trace-storage[ui]", "-q"])
        console.print("[green]✅ UI dependencies ready.[/green]\n")
    else:
        console.print("[dim]Skipping UI installation.[/dim]\n")

    # ------------------------------------------------------------------
    # Step 3 — Google Cloud Setup
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 3 of 5 — Google Cloud Credentials[/bold]")
    if not settings.credentials_path.exists():
        console.print(
            "\n[yellow]No credentials.json found.[/yellow] We'll start the guided setup wizard."
        )
        # Use subprocess to avoid typer-decoration issues
        subprocess.run([sys.executable, "-m", "docto_trace", "setup"], check=False)
    else:
        console.print(f"\n[green]✅ Using existing credentials at [dim]{settings.credentials_path}[/dim][/green]\n")

    # ------------------------------------------------------------------
    # Step 4 — Authentication (Login)
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 4 of 5 — Authenticate with Google[/bold]")
    if not settings.token_path.exists():
        # Use subprocess to avoid typer-decoration issues
        subprocess.run([sys.executable, "-m", "docto_trace", "login"], check=False)
    else:
        console.print(f"\n[green]✅ Already authenticated ([dim]{settings.token_path}[/dim])[/green]\n")

    # ------------------------------------------------------------------
    # Step 5 — AI Readiness (LLM)
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 5 of 5 — AI-Readiness (Optional)[/bold]")
    
    # Check for existing config
    current_model = settings.llm_model
    existing_key = None
    provider_detected = None
    
    if current_model:
        low_model = current_model.lower()
        if "gpt" in low_model: provider_detected = "openai"
        elif "claude" in low_model: provider_detected = "anthropic"
        elif "gemini" in low_model: provider_detected = "google"
        elif "groq" in low_model: provider_detected = "groq"
        
        if provider_detected:
            env_var = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GEMINI_API_KEY",
                "groq": "GROQ_API_KEY",
            }.get(provider_detected)
            # Check os.environ (which includes .env values because of load_dotenv() in config.py)
            if env_var:
                existing_key = os.environ.get(env_var)

    if current_model and existing_key:
        console.print(f"\n[green]✅ AI configuration already exists:[/green]")
        console.print(f"   [bold]Model:[/bold]    [dim]{current_model}[/dim]")
        console.print(f"   [bold]API Key:[/bold]  [dim]******** (Found in environment)[/dim]\n")
        
        if Confirm.ask("  Do you want to [bold]update[/bold] this AI configuration?", default=False):
            proceed_with_wizard = True
        else:
            proceed_with_wizard = False
            console.print("\n[dim]Using existing AI configuration.[/dim]\n")
    else:
        proceed_with_wizard = Confirm.ask(
            "\n  Enable [bold]AI-enhanced analysis[/bold] to get automated action plans?",
            default=True,
        )

    if proceed_with_wizard:
        import questionary
        
        provider = questionary.select(
            "Select your LLM Provider:",
            choices=[
                "openai",
                "anthropic",
                "google",
                "groq",
                "other"
            ]
        ).ask()
        
        if not provider:
            raise typer.Exit(code=1)
        
        model_map = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-latest",
            "google": "gemini/gemini-1.5-pro",
            "groq": "groq/llama-3.3-70b-versatile",
            "other": "model-name",
        }
        
        default_model = model_map.get(provider, "model-name")
        model_name = Prompt.ask(f"  Enter the model name for {provider}", default=default_model)
        
        # Determine the env var name for the API key
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        env_var = key_map.get(provider, f"{provider.upper()}_API_KEY")
        
        api_key = Prompt.ask(
            f"  Enter your [bold]{env_var}[/bold] (stored only locally in .env)",
            password=False,
        ).strip()

        # Persist to .env
        _update_env_file({
            "DOCTO_TRACE_LLM_MODEL": model_name,
            env_var: api_key,
        })
        console.print("\n[green]✅ AI configuration saved to .env[/green]\n")
    else:
        # If we skipped because of existing config, we don't show "Skipping"
        if not (current_model and existing_key):
            console.print("\n[dim]Skipping AI configuration.[/dim]\n")

    # ------------------------------------------------------------------
    # Final Step — Run Scan
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold green]All systems go! 🚀[/bold green]")
    if Confirm.ask("\n  Start your first scan now?", default=True):
        import questionary
        source = questionary.select(
            "What do you want to scan first?",
            choices=[
                "Google Drive",
                "Local File System"
            ]
        ).ask()
        
        cmd = [sys.executable, "-m", "docto_trace", "scan"]
        
        if source == "Local File System":
            home = str(Path.home())
            common_paths = {
                f"Current Directory ({os.getcwd()})": os.getcwd(),
                f"Home Directory ({home})": home,
                "Desktop": str(Path.home() / "Desktop"),
                "Documents": str(Path.home() / "Documents"),
                "Downloads": str(Path.home() / "Downloads"),
                "Custom Path...": "CUSTOM"
            }
            
            # Filter only existing paths
            choices = [k for k, v in common_paths.items() if v == "CUSTOM" or os.path.exists(v)]
            
            path_choice = questionary.select(
                "Which folder do you want to scan?",
                choices=choices
            ).ask()
            
            if not path_choice:
                raise typer.Exit(code=1)
                
            root_path = common_paths[path_choice]
            
            if root_path == "CUSTOM":
                console.print("\n[dim]💡 Tip: You can drag and drop a folder into this terminal window.[/dim]")
                root_path = Prompt.ask("  Enter the absolute path to scan").strip()
                # Remove quotes often added by OS drag-and-drop
                root_path = root_path.replace("'", "").replace('"', "")
            
            if not os.path.exists(root_path):
                console.print(f"[bold red]❌ Error:[/bold red] Path does not exist: {root_path}")
                raise typer.Exit(code=1)
                
            cmd.extend(["--source", "local", "--root-id", root_path])
        else:
            cmd.extend(["--source", "google"])

        if not install_ui:
            cmd.append("--no-ui")
            
        console.print(f"\n[bold cyan]Starting {source} scan...[/bold cyan]")
        subprocess.run(cmd, check=False)
    else:
        console.print(
            "\nSetup complete. You can run a scan anytime with:\n"
            "  [bold cyan]docto-trace scan[/bold cyan]"
        )


def _run_command(cmd: list[str]) -> None:
    """Helper to run a shell command and handle errors."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        err_console.print(f"[bold red]Error running command:[/bold red] {' '.join(cmd)}")
        err_console.print(f"[dim]{e.stderr}[/dim]")
        raise typer.Exit(code=1) from e


def _update_env_file(variables: dict[str, str]) -> None:
    """Update or create the .env file with the given variables."""
    env_path = Path(".env")
    
    # Read existing content
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    
    updated_keys = set()
    new_lines = []
    
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key, _ = line.split("=", 1)
            key = key.strip()
            if key in variables:
                new_lines.append(f"{key}={variables[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)
    
    # Add any keys that weren't in the original file
    for key, val in variables.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}")
            
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
