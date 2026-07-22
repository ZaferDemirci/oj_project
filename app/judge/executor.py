import asyncio
import subprocess
import sys
import tempfile
import os
import time
import shutil

async def run_single_testcase(
    source_code: str,
    test_input: str,
    time_limit: float,) -> dict:
    """
    Execute a single testcase in an isolated subprocess using subprocess.run inside asyncio.to_thread to avoid Windows event loop issues.
    """
    temp_dir = None
    try:
        # Create temporary directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        base_temp_dir = os.path.join(project_root, "temp")
        os.makedirs(base_temp_dir, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="oj_judge_", dir=base_temp_dir)
        
        source_path = os.path.join(temp_dir, "main.py")
        
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_code)
        
        cmd = [sys.executable, source_path]
        
        def _sync_run():
            start_time = time.perf_counter()
            try:
                # Run subprocess with timeout and UTF-8 decoding
                # If the output is not valid UTF-8, it raises UnicodeDecodeError
                proc_result = subprocess.run(
                    cmd,
                    input=test_input,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',   # UTF-8 decoding
                    errors='strict',    # Raise exception on invalid bytes
                    cwd=temp_dir,
                    timeout=time_limit,
                )
                end_time = time.perf_counter()
                
                return {
                    "stdout": proc_result.stdout,
                    "stderr": proc_result.stderr,
                    "exit_code": proc_result.returncode,
                    "time_used": end_time - start_time,
                    "timed_out": False,
                    "error": None,
                }
                
            except subprocess.TimeoutExpired:
                end_time = time.perf_counter()
                # Time limit exceeded
                return {
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "time_used": time_limit,
                    "timed_out": True,
                    "error": None,
                }
            except UnicodeDecodeError:
                # Non-UTF-8 output -> Runtime Error (RE)
                # The manager will see exit_code != 0 and treat it as RE
                end_time = time.perf_counter()
                return {
                    "stdout": "",
                    "stderr": "Output contains non-UTF-8 characters",
                    "exit_code": 1,  # Non-zero exit -> RE
                    "time_used": end_time - start_time,
                    "timed_out": False,
                    "error": None,
                }
            except Exception as e:
                # Any other judge-side error (e.g., file permissions)
                end_time = time.perf_counter()
                return {
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                    "time_used": 0.0,
                    "timed_out": False,
                    "error": f"Judge system error: {str(e)}",
                }
        
        # Run the synchronous function in a separate thread
        return await asyncio.to_thread(_sync_run)
        
    except Exception as e:
        # Catch any exception from the async wrapper itself
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "time_used": 0.0,
            "timed_out": False,
            "error": f"Judge system error: {str(e)}",
        }
    finally:
        # Remove temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Best effort cleanup