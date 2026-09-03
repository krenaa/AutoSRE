import ast
import os
import subprocess
from typing import Dict, List, Optional
import httpx
from fastmcp import FastMCP

mcp = FastMCP("AutoSRE-Operations-Workbench")


# ==========================================
# 1. TEST & CODE DIAGNOSTICS TOOLS
# ==========================================

@mcp.tool()
def run_pytest(test_target: str = "tests/", verbose: bool = True) -> Dict[str, object]:
    """Runs pytest on target path or test file and returns structured output."""
    cmd = ["pytest"]
    if verbose:
        cmd.append("-v")
    cmd.append(test_target)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@mcp.tool()
def run_syntax_check(file_path: str) -> Dict[str, object]:
    """Validates Python syntax using AST parser before writing or verifying code."""
    if not os.path.exists(file_path):
        return {"valid": False, "error": f"File '{file_path}' does not exist."}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code, filename=file_path)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}",
        }


@mcp.tool()
def run_linter(file_path: str) -> Dict[str, object]:
    """Runs flake8 style and quality check on a file."""
    if not os.path.exists(file_path):
        return {"clean": False, "output": f"File '{file_path}' not found."}
    result = subprocess.run(
        ["flake8", file_path, "--max-line-length=100"],
        capture_output=True,
        text=True,
    )
    return {
        "clean": result.returncode == 0,
        "violations": result.stdout.strip().splitlines(),
    }


# ==========================================
# 2. CODEBASE DISCOVERY & INSPECTION TOOLS
# ==========================================

@mcp.tool()
def list_directory_tree(base_path: str = ".", max_depth: int = 3) -> List[str]:
    """Recursively lists files and directories up to max_depth, ignoring venv and cache."""
    ignored = {"venv", ".venv", "__pycache__", ".git", ".pytest_cache"}
    tree = []
    base_path = os.path.abspath(base_path)

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignored]
        rel_root = os.path.relpath(root, base_path)
        depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        if depth > max_depth:
            continue
        for file in files:
            rel_file = os.path.join(rel_root, file) if rel_root != "." else file
            tree.append(rel_file.replace("\\", "/"))
    return sorted(tree)


@mcp.tool()
def read_source_file(
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, object]:
    """Reads source file content with line numbers for precise debugging."""
    if not os.path.exists(file_path):
        return {"found": False, "error": f"File '{file_path}' not found."}
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    s = max(1, start_line) if start_line else 1
    e = min(total_lines, end_line) if end_line else total_lines

    numbered_content = [
        f"{idx}: {line}" for idx, line in enumerate(lines[s - 1 : e], start=s)
    ]
    return {
        "found": True,
        "total_lines": total_lines,
        "view_window": f"{s}-{e}",
        "content": "".join(numbered_content),
        "raw_code": "".join(lines[s - 1 : e]),
    }


@mcp.tool()
def apply_code_patch(file_path: str, patch_content: str) -> Dict[str, object]:
    """Safely applies code patch to file after verifying Python syntax."""
    try:
        # Pre-validate syntax before committing write
        ast.parse(patch_content, filename=file_path)
    except SyntaxError as e:
        return {
            "success": False,
            "error": f"Patch rejected: Syntax error on line {e.lineno}: {e.msg}",
        }

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(patch_content)
        return {"success": True, "error": None, "file": file_path}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ==========================================
# 3. GIT FORENSICS & ROLLBACK TOOLS
# ==========================================

@mcp.tool()
def get_git_diff(file_path: Optional[str] = None) -> str:
    """Returns the uncommitted git diff against HEAD."""
    cmd = ["git", "diff"]
    if file_path:
        cmd.append(file_path)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout if result.stdout else "No unstaged changes detected."


@mcp.tool()
def get_recent_commits(limit: int = 5) -> List[str]:
    """Fetches recent git commit summaries to identify regression points."""
    result = subprocess.run(
        ["git", "log", f"-n{limit}", "--oneline"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().splitlines()
    return ["No git history found."]


@mcp.tool()
def revert_file_to_head(file_path: str) -> Dict[str, object]:
    """Reverts changes in a file back to git HEAD state (safe rollback)."""
    result = subprocess.run(
        ["git", "checkout", "HEAD", "--", file_path],
        capture_output=True,
        text=True,
    )
    return {
        "reverted": result.returncode == 0,
        "message": f"Reverted {file_path} to HEAD" if result.returncode == 0 else result.stderr,
    }


# ==========================================
# 4. TELEMETRY & NETWORK HEALTH TOOLS
# ==========================================

@mcp.tool()
def probe_http_endpoint(url: str, timeout_sec: float = 3.0) -> Dict[str, object]:
    """Checks HTTP endpoint status, latency, and response headers."""
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(url)
            return {
                "reachable": True,
                "status_code": resp.status_code,
                "latency_ms": round(resp.elapsed.total_seconds() * 1000, 2),
            }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()