import os
import subprocess
import psutil  # Use psutil to check for running processes
import fastapi

app = fastapi.FastAPI(docs_url=None, redoc_url=None)

# Path to the script you want to run
script_path = "/app/trendshift.py"


# Function to check if the script is already running
def is_script_running(script_name: str):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if script_name in proc.info['cmdline']:
            return proc
    return None


@app.get("/run")
def run(password: str):
    # Check password
    if password != os.environ.get("RunPassword", "Test@1sa"):
        return {"status": "Invalid Password"}

    # Check if the script is already running
    if is_script_running(script_path):
        return {"status": "Script is already running"}

    # Start the script if not already running
    subprocess.Popen(["/usr/local/bin/python", script_path])
    return {"status": "OK"}


@app.get("/stop")
def stop(password: str):
    if password != os.environ.get("RunPassword", "Test@1sa"):
        return {"status": "Invalid Password"}

    proc = is_script_running(script_path)
    if proc:
        proc.terminate()  # Gracefully terminate the process
        proc.wait()  # Wait for the process to terminate
        return {"status": "Script stopped"}

    return {"status": "Script is not running"}

