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
    is_venv = sys.prefix != sys.base_prefix
    venv_dir = Path(".venv")
    
    # Path to venv's python executable
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not is_venv:
        console.print(
            "\n[yellow]⚠️  You are not running in a virtual environment.[/yellow]\n"
            "It is highly recommended to use a venv to keep your global Python clean.\n"
        )
        if not venv_dir.exists():
            if Confirm.ask("  Create a virtual environment in [bold].venv/[/bold] now?", default=True):
                _run_command([sys.executable, "-m", "venv", str(venv_dir)])
                console.print("\n[green]✅ Virtual environment created.[/green]")
        
        # Transition automatically
        if venv_python.exists():
            console.print(
                f"\n[bold green]🚀 Transitioning to virtual environment...[/bold green]\n"
                f"[dim]Re-spawning: {venv_python} -m docto_trace onboard[/dim]\n"
            )
            # Use os.execv to REPLACE the current process with the venv python
            # This is the "magic" that makes it seamless.
            # We need to add the current directory to PYTHONPATH so it finds 'docto_trace'
            # before it's even installed in the venv.
            os.environ["PYTHONPATH"] = os.getcwd()
            args = [str(venv_python), "-m", "docto_trace", "onboard"]
            os.execv(args[0], args)
        else:
            console.print(
                "\n[red]❌ Could not find virtual environment python.[/red] "
                "Please activate it manually."
            )
            raise typer.Exit(code=1)
    else:
        console.print(f"\n[green]✅ Running in virtual environment:[/green] [dim]{sys.prefix}[/dim]\n")

    # ------------------------------------------------------------------
    # Step 2 — Install Dependencies
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold]Step 2 of 5 — Dependencies & UI[/bold]")
    install_ui = Confirm.ask(
        "\n  Do you want to install the [bold]Interactive UI[/bold]? (requires streamlit/plotly)",
        default=True,
    )
    
    extras = "[ui]" if install_ui else ""
    
    # Use a Rich status spinner for feedback
    with console.status(f"[bold]📦 Installing docto-trace-storage{extras}…[/bold]", spinner="dots"):
        # We use -e . so it's always up to date during development
        _run_command([sys.executable, "-m", "pip", "install", "-e", f".{extras}", "-q"])
    
    console.print("[green]✅ Dependencies installed.[/green]\n")

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
    use_llm = Confirm.ask(
        "\n  Enable [bold]AI-enhanced analysis[/bold] to get automated action plans?",
        default=True,
    )

    if use_llm:
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
        console.print("\n[dim]Skipping AI configuration.[/dim]\n")

    # ------------------------------------------------------------------
    # Final Step — Run Scan
    # ------------------------------------------------------------------
    console.print()
    console.rule("[bold green]All systems go! 🚀[/bold green]")
    if Confirm.ask("\n  Start your first scan now?", default=True):
        console.print("\n[bold cyan]Starting scan...[/bold cyan]")
        
        # We run it as a subprocess to ensure clean exit/entry and proper typer handling
        cmd = [sys.executable, "-m", "docto_trace", "scan"]
        if not install_ui:
            cmd.append("--no-ui")
            
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
