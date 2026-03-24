"""
Phase 4 Engine — AI Readiness and Digital Chaos evaluation.

Calculates the structured vs unstructured ratio, analyzes file naming mathematically,
and optionally uses an LLM to generate a qualitative report.
"""

from __future__ import annotations

import asyncio
import random
import re
from typing import Generator

from docto_trace.schemas.report import AIReadinessScore, FileTypeCategory
from docto_trace.schemas.storage import FileNode, FolderNode, StorageTree

# Known structured formats
_STRUCTURED_EXTENSIONS = {
    ".csv", ".json", ".xml", ".xls", ".xlsx", ".sqlite", ".db", 
    ".yaml", ".yml", ".toml", ".parquet", ".tsv"
}
_STRUCTURED_MIMETYPES = {
    "application/json",
    "text/csv",
    "application/xml",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Regex for generic auto-generated names (IMG_1234, DSC001, Screenshot 2023...)
_AUTO_GEN_RE = re.compile(
    r"^(img|dsc|dcim|screenshot|untitled|document|copy of)[\s_-]*\d*",
    re.IGNORECASE
)
_DATE_RE = re.compile(r"(20\d{2}[-_]\d{2}[-_]\d{2}|20[1-2]\d|19[8-9]\d)")


def _iter_files(node: FolderNode) -> Generator[tuple[FileNode, str], None, None]:
    """Iterate all files recursively to avoid cyclical imports from auditor.py."""
    stack: list[tuple[FolderNode, str]] = [(node, node.name)]
    while stack:
        current, path = stack.pop()
        for child in current.children:
            if isinstance(child, FolderNode):
                stack.append((child, f"{path}/{child.name}"))
            else:
                yield child, f"{path}/{child.name}"


def _categorize_file(file_node: FileNode) -> FileTypeCategory:
    """Classify a file as STRUCTURED or UNSTRUCTURED."""
    # Check mime type first
    if file_node.mime_type in _STRUCTURED_MIMETYPES:
        return FileTypeCategory.STRUCTURED
    
    # Check extension
    name_lower = file_node.name.lower()
    if any(name_lower.endswith(ext) for ext in _STRUCTURED_EXTENSIONS):
        return FileTypeCategory.STRUCTURED
        
    # By default, everything else is unstructured for AI context (pdfs, images, loose docs)
    return FileTypeCategory.UNSTRUCTURED


def _score_naming_entropy(name: str) -> float:
    """
    Programmatic heuristic to score how descriptive a filename is (0-100).
    Higher is better (more descriptive, more "AI ready").
    """
    # Remove extension
    base_name = name.rsplit(".", 1)[0] if "." in name else name
    base_name = base_name.strip()
    
    if not base_name:
        return 0.0

    # Auto-generated or completely numeric names are bad
    if base_name.isdigit() or _AUTO_GEN_RE.match(base_name):
        return 10.0
        
    # Very short names without delimiters
    if len(base_name) <= 4:
        return 20.0

    # Split by common delimiters (space, underscore, dash)
    words = [w for w in re.split(r"[\s_\-]+", base_name) if w]
    num_words = len(words)
    
    if num_words == 1:
        score = 30.0
    elif num_words == 2:
        score = 60.0
    elif num_words >= 3:
        score = 80.0
    else:
        score = 10.0  # Should not happen if base_name is not empty
        
    # Bonus for timestamps/dates (shows organization)
    if _DATE_RE.search(base_name):
        score += 20.0
        
    return min(100.0, score)


def build_ai_readiness_summary(
    tree: StorageTree,
    llm_model: str | None = None,
    max_agent_iterations: int = 30,
    source: str = "google",
) -> AIReadinessScore:
    """
    Calculate the AI Readiness ratio and naming entropy.
    If llm_model is provided, calls LiteLLM to generate a qualitative report.
    """
    structured_count = 0
    unstructured_count = 0
    structured_bytes = 0
    unstructured_bytes = 0
    
    total_entropy = 0.0

    for file_node, _path in _iter_files(tree.tree):
        cat = _categorize_file(file_node)
        size = file_node.effective_size_bytes
        
        if cat == FileTypeCategory.STRUCTURED:
            structured_count += 1
            structured_bytes += size
        else:
            unstructured_count += 1
            unstructured_bytes += size
            
        total_entropy += _score_naming_entropy(file_node.name)
        
    avg_entropy = 0.0
    if tree.total_files > 0:
        avg_entropy = total_entropy / tree.total_files
        
    # Map-Reduce LLM Analysis
    ai_analysis_report = None
    if llm_model is not None:
        from rich.console import Console
        err_console = Console(stderr=True)
        err_console.print(f"[bold cyan]🤖 AI Readiness Analysis using model:[/bold cyan] [green]{llm_model}[/green]")
        
        # Generate the top-level tree map (depth 2) for structural context
        tree_map = _build_tree_map(tree.tree, max_depth=2)
        
        # Run the autonomous agent loop
        try:
            ai_analysis_report = asyncio.run(_run_autonomous_agent(
                llm_model=llm_model,
                tree=tree,
                structured_count=structured_count,
                unstructured_count=unstructured_count,
                avg_entropy=avg_entropy,
                max_iterations=max_agent_iterations,
                source=source
            ))
        except Exception as e:
            from rich.console import Console
            err_console = Console(stderr=True)
            err_console.print(f"[yellow]⚠️  LLM Analysis failed: {e}[/yellow]")

    return AIReadinessScore(
        structured_files_count=structured_count,
        unstructured_files_count=unstructured_count,
        structured_bytes=structured_bytes,
        unstructured_bytes=unstructured_bytes,
        naming_entropy_score=round(float(avg_entropy), 1),
        ai_analysis_report=ai_analysis_report
    )


def _build_tree_map(node: FolderNode, max_depth: int, current_depth: int = 0) -> str:
    """Generate a lightweight textual representation of the top directory structure."""
    if current_depth > max_depth:
        return ""
    
    indent = "    " * current_depth
    prefix = "├── " if current_depth > 0 else ""
    lines = [f"{indent}{prefix}{node.name}/ ({node.total_file_count} files, {node.total_size_bytes // (1024*1024)} MB)"]
    
    # Only recurse into folders
    subfolders = [c for c in node.children if isinstance(c, FolderNode)]
    # Sort by size descending
    subfolders.sort(key=lambda f: f.total_size_bytes, reverse=True)
    
    for child in subfolders[:10]: # cap at top 10 subfolders per folder
        child_str = _build_tree_map(child, max_depth, current_depth + 1)
        if child_str:
            lines.append(child_str)
            
    if len(subfolders) > 10:
        lines.append(f"{indent}    └── ... and {len(subfolders)-10} more folders")
        
    return "\n".join(lines)


async def _run_autonomous_agent(
    llm_model: str,
    tree: StorageTree,
    structured_count: int,
    unstructured_count: int,
    avg_entropy: float,
    max_iterations: int = 30,
    source: str = "google",
) -> str:
    """Run an autonomous ReAct loop using Tool Calling to navigate the tree."""
    import json
    import litellm
    from rich.console import Console
    litellm.drop_params = True
    err_console = Console(stderr=True)

    # Dictionary for O(1) folder path resolutions
    def _build_folder_dict(node: FolderNode, current_path: str) -> dict[str, FolderNode]:
        d = {current_path: node}
        for child in node.children:
            if isinstance(child, FolderNode):
                d.update(_build_folder_dict(child, f"{current_path}/{child.name}"))
        return d

    root_name = tree.tree.name
    folder_dict = _build_folder_dict(tree.tree, root_name)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "explore_folder",
                "description": "Returns the sub-folder structure and sizes for a given folder path. Use this to navigate the drive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder_path": {
                            "type": "string",
                            "description": f"The full path to the folder. Start with '{root_name}'"
                        }
                    },
                    "required": ["folder_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sample_files",
                "description": "Returns a random sample of up to 50 files directly inside a specific folder to inspect naming and types.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder_path": {
                            "type": "string",
                            "description": "The full path to the folder."
                        }
                    },
                    "required": ["folder_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "record_checkpoint",
                "description": "Records an insight into your scratchpad memory. This does not finish the analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "insight": {
                            "type": "string",
                            "description": "Your deduction or finding."
                        }
                    },
                    "required": ["insight"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "finalize_report",
                "description": "Submits the final qualitative review and action plan. Call this ONLY when you have explored enough.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "executive_summary": {
                            "type": "string",
                            "description": "A high-level executive summary of the digital state and AI readiness."
                        },
                        "semantic_clarity_score": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Score from 1-10 on how clear and descriptive the file naming and structure are."
                        },
                        "retrieval_confidence_score": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Score from 1-10 on how easy it would be for an AI to retrieve specific information."
                        },
                        "automation_potential_score": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "Score from 1-10 on how ready the data is for automated processing/RAG."
                        },
                        "ai_assessment_summary": {
                            "type": "string",
                            "description": "A single sentence summarizing the overall AI readiness."
                        },
                        "efficiency_strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of structural and organizational strengths found."
                        },
                        "critical_weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of critical organizational weaknesses found."
                        },
                        "action_plan": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "priority": {
                                        "type": "string",
                                        "enum": ["CRITICAL", "HIGH", "MEDIUM"]
                                    },
                                    "action_item": {
                                        "type": "string",
                                        "description": "The specific task name or action."
                                    },
                                    "target_outcome": {
                                        "type": "string",
                                        "description": "The goal or result of the action."
                                    }
                                },
                                "required": ["priority", "action_item", "target_outcome"]
                            },
                            "description": "A prioritized list of action items."
                        },
                        "recommendations": {
                            "type": "string",
                            "description": "Final strategic recommendations."
                        }
                    },
                    "required": [
                        "executive_summary", 
                        "semantic_clarity_score", 
                        "retrieval_confidence_score", 
                        "automation_potential_score",
                        "ai_assessment_summary",
                        "efficiency_strengths",
                        "critical_weaknesses",
                        "action_plan",
                        "recommendations"
                    ]
                }
            }
        }
    ]

    top_tree_map = _build_tree_map(tree.tree, max_depth=1)
    
    source_name = "Google Drive" if source == "google" else "Local File System"
    
    import typing
    messages: list[dict[str, typing.Any]] = [
        {
            "role": "system", 
            "content": (
                f"You are an Autonomous AI Data Archivist analyzing a {source_name} to evaluate its organizational health and AI Readiness.\n\n"
                f"Your goal is to explore the {source_name.lower()}, identify structural patterns, naming conventions, and data silos to produce a comprehensive report.\n\n"
                f"Use your tools iteratively to explore folders and files. Record checkpoints of findings. Once thoroughly explored (max {max_iterations} turns), finalize the report.\n\n"
                "When calling `finalize_report`, ensure you provide:\n"
                "- Executive Summary: High-level overview.\n"
                "- Readiness Assessment Scores (1-10) for Semantic Clarity (naming quality), Retrieval Confidence (findability), and Automation Potential (RAG readiness).\n"
                "- AI Assessment Summary: A punchy one-sentence summary.\n"
                "- Structural Diagnostics: Bullet points for Efficiency Strengths and Critical Weaknesses.\n"
                "- Action Plan (Prioritized): At least 3 prioritized action items (CRITICAL, HIGH, MEDIUM) with specific tasks and target outcomes.\n"
                "- Recommendations: Strategic long-term advice."
            )
        },
        {"role": "user", "content": f"Global Setup Metrics:\n- Structured: {structured_count}\n- Unstructured: {unstructured_count}\n- Naming Entropy: {avg_entropy:.1f}/100.0\n\nTop-level Map:\n{top_tree_map}\n\nBegin your exploration."}
    ]

    warning_threshold = int(max_iterations * 0.8)
    for iteration in range(max_iterations):
        steps_left = max_iterations - iteration
        
        # Inject system warnings preventing abrupt termination
        if iteration == max_iterations - 1:
            messages.append({"role": "user", "content": f"CRITICAL SYSTEM WARNING: This is your absolute final step ({steps_left} left). You MUST call `finalize_report` now or your session will be forcibly terminated and progress lost."})
            err_console.print(f"[dim]🚨 Sent final step warning to Agent ({steps_left} left).[/dim]")
        elif iteration >= warning_threshold:
            messages.append({"role": "user", "content": f"SYSTEM WARNING: You only have {steps_left} exploration steps left! You must rapidly prepare to submit your conclusions via `finalize_report`."})
            err_console.print(f"[dim]⚠️ Sent loop limit warning to Agent ({steps_left} left).[/dim]")

        response = await litellm.acompletion(
            model=llm_model,
            messages=messages,
            tools=tools,
            temperature=0.2
        )
        msg = response.choices[0].message
        
        # Append the assistant's message to the conversation
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [dict(tc) for tc in msg.tool_calls] if msg.tool_calls else None
        })

        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception:
                    args = {}

                tool_result = ""

                if func_name == "explore_folder":
                    path = args.get("folder_path", "")
                    err_console.print(f"[dim]🤖 Agent action: explore_folder('{path}')[/dim]")
                    if path in folder_dict:
                        tool_result = _build_tree_map(folder_dict[path], max_depth=1)
                    else:
                        tool_result = f"Error: Folder '{path}' not found."

                elif func_name == "sample_files":
                    path = args.get("folder_path", "")
                    err_console.print(f"[dim]🤖 Agent action: sample_files('{path}')[/dim]")
                    if path in folder_dict:
                        fnode = folder_dict[path]
                        # Flat list of specific file children
                        files = [c for c in fnode.children if isinstance(c, FileNode)]
                        random.shuffle(files)
                        sample = files[:50]
                        if sample:
                            tool_result = "\n".join(f"- {f.name} ({f.effective_size_bytes}B)" for f in sample)
                        else:
                            tool_result = "No files found strictly in this folder level."
                    else:
                        tool_result = f"Error: Folder '{path}' not found."

                elif func_name == "record_checkpoint":
                    insight = args.get("insight", "")
                    err_console.print(f"[blue]💡 Agent checkpoint:[/blue] [dim]{insight}[/dim]")
                    tool_result = "Checkpoint recorded inside memory."

                elif func_name == "finalize_report":
                    err_console.print(f"[bold green]✅ Agent successfully finalized report.[/bold green]")
                    
                    # Score-to-Risk conversion
                    def _risk_level(score):
                        if score >= 8: return "LOW"
                        if score >= 4: return "MED"
                        return "HIGH"

                    exec_sum = args.get("executive_summary", "")
                    s_score = args.get("semantic_clarity_score", 1)
                    r_score = args.get("retrieval_confidence_score", 1)
                    a_score = args.get("automation_potential_score", 1)
                    assessment = args.get("ai_assessment_summary", "")
                    
                    strengths = args.get("efficiency_strengths", [])
                    weaknesses = args.get("critical_weaknesses", [])
                    actions = args.get("action_plan", [])
                    recs = args.get("recommendations", "")

                    # Build Markdown report
                    md = f"**Executive Summary:** {exec_sum}\n\n"
                    md += "## Readiness Assessment\n"
                    md += "*Evaluation of data legibility for LLMs and RAG systems.*\n\n"
                    md += "| Metric | Score | Risk Level |\n"
                    md += "| :--- | :--- | :--- |\n"
                    md += f"| **Semantic Clarity** | {s_score}/10 | {_risk_level(s_score)} |\n"
                    md += f"| **Retrieval Confidence** | {r_score}/10 | {_risk_level(r_score)} |\n"
                    md += f"| **Automation Potential** | {a_score}/10 | {_risk_level(a_score)} |\n\n"
                    md += f"**Assessment:** {assessment}\n\n"
                    
                    md += "## Structural Diagnostics\n\n"
                    md += "### ✅ Efficiency Strengths\n"
                    for s in strengths:
                        md += f"- {s}\n"
                    md += "\n### ❌ Critical Weaknesses\n"
                    for w in weaknesses:
                        md += f"- {w}\n"
                    md += "\n"
                    
                    md += "## Action Plan (Prioritized)\n\n"
                    md += "| Priority | Action Item | Target Outcome |\n"
                    md += "| :--- | :--- | :--- |\n"
                    for action in actions:
                        p = action.get("priority", "MEDIUM")
                        ai = action.get("action_item", "")
                        to = action.get("target_outcome", "")
                        md += f"| **{p}** | {ai} | {to} |\n"
                    md += "\n"
                    
                    md += "## Recommendations\n"
                    md += f"{recs}"
                    
                    return md

                # Append tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": tool_result
                })
        else:
            # If the model randomly stopped using tools and gave text, wrap it up
            return msg.content or "No findings reported."

    err_console.print(f"[dim]⚠️ Agent reached iteration limit of {max_iterations} loops.[/dim]")
    return "Analysis incomplete. The agent hit the exploration loop limit before submitting a final report."


