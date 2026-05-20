import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")
REPORT_ENDPOINT = "/api/agent/report"
AGENT_NAME = "cross-platform-agent"
AGENT_SECRET = os.environ.get("AGENT_SECRET", "")
JOB_POLL_ENDPOINT = "/api/agent/jobs"
JOB_RESULT_ENDPOINT = "/api/agent/job-result"

