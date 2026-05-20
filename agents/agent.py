import argparse
import os
import platform
import shlex
import subprocess
import tempfile
from urllib.parse import urlparse

import requests
from agents.config import (
    BACKEND_URL,
    REPORT_ENDPOINT,
    AGENT_SECRET,
    JOB_POLL_ENDPOINT,
    JOB_RESULT_ENDPOINT,
)
from agents.system_info import metrics_payload


def build_installer_command(installer_path, installer_ext, install_args):
    args = shlex.split(install_args) if install_args else []
    if installer_ext == '.msi':
        return ['msiexec', '/i', installer_path, '/quiet', '/norestart'] + args
    return [installer_path] + (args or ['/quiet', '/norestart'])


def is_windows_admin():
    if platform.system() != 'Windows':
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def download_installer(download_url):
    response = requests.get(download_url, stream=True, timeout=60)
    response.raise_for_status()
    parsed = urlparse(download_url)
    suffix = os.path.splitext(parsed.path)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmp_file.write(chunk)
        return tmp_file.name


def run_installer_job(job):
    download_url = job.get('download_url')
    if not download_url:
        return {'status': 'failed', 'output': '', 'error': 'Missing download URL', 'return_code': 1}

    installer_ext = job.get('installer_ext', '').lower()
    install_args = job.get('install_args', '')

    if platform.system() == 'Windows' and not is_windows_admin():
        return {
            'status': 'failed',
            'output': '',
            'error': 'Windows installer jobs require the agent to run with administrative privileges. Install the agent as a Windows service or scheduled task with "Run with highest privileges".',
            'return_code': 1,
        }

    try:
        installer_path = download_installer(download_url)
    except requests.RequestException as exc:
        return {'status': 'failed', 'output': '', 'error': f'Failed to download installer: {exc}', 'return_code': 1}

    try:
        command = build_installer_command(installer_path, installer_ext, install_args)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return {
            'status': 'success' if result.returncode == 0 else 'failed',
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode,
        }
    except OSError as exc:
        return {'status': 'failed', 'output': '', 'error': str(exc), 'return_code': 1}
    finally:
        try:
            os.remove(installer_path)
        except OSError:
            pass


def report_job_result(job_id, result):
    result_url = f"{BACKEND_URL}{JOB_RESULT_ENDPOINT}"
    payload = {
        'job_id': job_id,
        'status': result['status'],
        'output': result.get('output', ''),
        'error': result.get('error', ''),
        'return_code': result.get('return_code'),
    }
    if AGENT_SECRET:
        payload['token'] = AGENT_SECRET

    try:
        response = requests.post(result_url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        print('Failed to report installer job result:', exc)
        return False


def fetch_agent_jobs(host, username, port):
    poll_url = f"{BACKEND_URL}{JOB_POLL_ENDPOINT}"
    params = {'host': host, 'username': username, 'port': port}
    if AGENT_SECRET:
        params['token'] = AGENT_SECRET

    response = requests.get(poll_url, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get('jobs', [])


def main():
    parser = argparse.ArgumentParser(description="Cross-platform monitoring agent for Linux and Windows hosts")
    parser.add_argument("--host", required=True, help="Server host or IP")
    parser.add_argument("--username", default="agent", help="Agent identity username")
    parser.add_argument("--port", default=22, type=int, help="SSH port for server identity (Linux) or RDP port (Windows)")
    args = parser.parse_args()

    report_url = f"{BACKEND_URL}{REPORT_ENDPOINT}"
    payload = metrics_payload(args.host, args.username, args.port)

    try:
        response = requests.post(report_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Report sent successfully", response.json())
    except requests.RequestException as exc:
        print("Failed to send report:", exc)

    try:
        jobs = fetch_agent_jobs(args.host, args.username, args.port)
        for job in jobs:
            print(f"Execution job received: {job.get('job_id')} -> {job.get('installer_name')}")
            result = run_installer_job(job)
            report_job_result(job.get('job_id'), result)
    except requests.RequestException as exc:
        print('Failed to fetch agent jobs:', exc)


if __name__ == "__main__":
    main()
