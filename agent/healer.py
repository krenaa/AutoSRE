import os
import subprocess
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TARGET_FILE = os.path.join("target", "app.py")


def run_tests() -> tuple[bool, str]:
    """Runs pytest and returns (passed: bool, output: str)."""
    result = subprocess.run(
        ["pytest"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout + "\n" + result.stderr


def request_code_repair(broken_code: str, error_trace: str) -> str:
    """Sends broken code and test trace to Groq to generate the patch."""
    prompt = f"""You are an autonomous Site Reliability & Software Engineer.
A unit test failed with the following traceback:

--- TRACE START ---
{error_trace}
--- TRACE END ---

Here is the source code containing the bug:

--- CODE START ---
{broken_code}
--- CODE END ---

Task:
Fix the bug so all tests pass.
Return ONLY valid Python code for target/app.py.
Do NOT enclose your answer in markdown code blocks.
Do NOT write explanations.
"""
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    clean_code = response.choices[0].message.content.strip()

    if clean_code.startswith("```python"):
        clean_code = clean_code[len("```python") :]
    elif clean_code.startswith("```"):
        clean_code = clean_code[len("```") :]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]

    return clean_code.strip()


def run_repair_pipeline():
    print("=" * 60)
    print("[STEP 1] Running test suite to detect failures...")
    print("=" * 60)

    passed, test_output = run_tests()
    if passed:
        print("All tests already pass. No repair needed.")
        return True

    print("Test failure detected! Trace excerpt:")
    for line in test_output.strip().splitlines()[-10:]:
        print(f"  {line}")

    print(f"\n[STEP 2] Reading target code from '{TARGET_FILE}'...")
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        broken_code = f.read()

    print("\n[STEP 3] Generating fix via LLM (qwen/qwen3.8-27b)...")
    repaired_code = request_code_repair(broken_code, test_output)

    print(f"\n[STEP 4] Writing patch to '{TARGET_FILE}'...")
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(repaired_code)

    print("\n[STEP 5] Re-running test suite to verify resolution...")
    re_passed, post_output = run_tests()

    if re_passed:
        print("=" * 60)
        print("SUCCESS: Agent resolved the incident and verified tests!")
        print("=" * 60)
        return True
    else:
        print("Patch applied, but tests still failed:")
        print(post_output)
        return False