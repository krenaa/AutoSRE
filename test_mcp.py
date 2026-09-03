from agent.mcp_server import (
    list_directory_tree,
    read_source_file,
    run_pytest,
    get_recent_commits,
    run_syntax_check,
)

print("=" * 60)
print("VERIFYING AUTOSRE MCP TOOLS")
print("=" * 60)

# 1. Test directory discovery
tree = list_directory_tree(".")
print(f"\n[Tool: list_directory_tree] Discovered {len(tree)} files:")
for item in tree[:6]:
    print(f"  - {item}")

# 2. Test reading file with line numbering
file_view = read_source_file("target/app.py", start_line=1, end_line=5)
print(f"\n[Tool: read_source_file] Reading target/app.py lines 1-5:")
print(file_view.get("content"))

# 3. Test running pytest via MCP
test_res = run_pytest("tests/")
print(f"\n[Tool: run_pytest] Passed: {test_res['passed']} (Exit Code: {test_res['exit_code']})")

# 4. Test syntax check
syntax_res = run_syntax_check("target/app.py")
print(f"\n[Tool: run_syntax_check] Valid Syntax: {syntax_res['valid']}")

# 5. Test Git forensics
commits = get_recent_commits(limit=3)
print(f"\n[Tool: get_recent_commits] Recent commits:")
for c in commits:
    print(f"  - {c}")

print("\n" + "=" * 60)
print("ALL MCP TOOLS OPERATIONAL")
print("=" * 60) 