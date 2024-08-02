import os
import subprocess
import fastapi

app = fastapi.FastAPI(docs_url=None, redoc_url=None)


# write a run url via shell script or another python script to run the server
@app.get("/run")
def run(password: str):
    if password != os.environ.get("RunPassword", "Test@1sa"):
        return {"status": "Invalid Password"}
    # os.system("/usr/local/bin/python /app/trendshift.py")
    subprocess.Popen(["/usr/local/bin/python", "/app/trendshift.py"])
    return {"status": "OK"}
