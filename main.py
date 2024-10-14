import os
import subprocess
import psutil  # Use psutil to check for running processes
import fastapi
from pydantic import BaseModel


class PasswordModel(BaseModel):
    password: str


class LinesModel(BaseModel):
    log_file_name: str = "logs.txt"
    lines: int = -1


app = fastapi.FastAPI(docs_url="/", redoc_url=None)

# Path to the script you want to run
script_path = "/app/trendshift.py"


# Function to check if the script is already running
def is_script_running(script_name: str):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if script_name in proc.info['cmdline']:
            return proc
    return None


@app.post("/run")
def run(password_obj: PasswordModel):
    # Check password
    if password_obj.password != os.environ.get("RunPassword", "Test@1sa"):
        return {"status": "Invalid Password"}

    # Check if the script is already running
    if is_script_running(script_path):
        return {"status": "Script is already running"}

    # Start the script if not already running
    subprocess.Popen(["/usr/local/bin/python", script_path])
    return {"status": "OK"}


@app.post("/stop")
def stop(password_obj: PasswordModel):
    if password_obj.password != os.environ.get("RunPassword", "Test@1sa"):
        return {"status": "Invalid Password"}

    proc = is_script_running(script_path)
    if proc:
        proc.terminate()  # Gracefully terminate the process
        proc.wait()  # Wait for the process to terminate
        return {"status": "Script stopped"}

    return {"status": "Script is not running"}


@app.post("/logs")
def get_logs(lines_obj: LinesModel):
    if lines_obj.lines == -1:
        with open(f"/app/logs/{lines_obj.log_file_name}") as f:
            logs = f.read()
    elif lines_obj.lines <= 0:
        return {"status": "Invalid number of lines"}
    else:
        # Read the last `lines` lines from the log file
        logs = subprocess.check_output(["tail", f"-{lines_obj.lines}", "/app/logs/logs.txt"], text=True)
    return fastapi.responses.PlainTextResponse(logs)

@app.post("/available-logs")
def available_logs():
    logs = os.listdir("/app/logs")
    return {"logs": logs}