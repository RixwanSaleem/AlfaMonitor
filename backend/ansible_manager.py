import os
import shutil
import subprocess
import tempfile
from tempfile import NamedTemporaryFile
from backend.crypto import decrypt_text


def _server_password(server):
    if isinstance(server, dict):
        return decrypt_text(server.get("password", "")) if server.get("password") else ""
    return decrypt_text(server.password) if server.password else ""


def _server_host(server):
    return server["host"] if isinstance(server, dict) else server.host


def _server_username(server):
    return server["username"] if isinstance(server, dict) else server.username


def _server_port(server):
    return server.get("port", 22) if isinstance(server, dict) else server.port


def write_inventory(servers):
    with NamedTemporaryFile(mode="w", delete=False) as inventory_file:
        for server in servers:
            pwd = _server_password(server)
            inventory_file.write(
                f"{_server_host(server)} ansible_user={_server_username(server)} ansible_ssh_pass={pwd} ansible_port={_server_port(server)}\n"
            )
        return inventory_file.name


def write_playbook(playbook_text):
    with NamedTemporaryFile(mode="w", delete=False, suffix=".yml") as playbook_file:
        playbook_file.write(playbook_text)
        return playbook_file.name


def run_playbook(servers, playbook_text=None):
    if not servers:
        return {"returncode": 1, "stdout": "", "stderr": "No servers provided to run playbook."}

    inventory_path = write_inventory(servers)
    temp_playbook_path = None
    temp_dir = None
    try:
        if playbook_text:
            temp_playbook_path = write_playbook(playbook_text)
            playbook_path = temp_playbook_path
        else:
            playbook_path = os.path.join(os.path.dirname(__file__), "../ansible/playbook.yml")

        playbook_cmd = shutil.which("ansible-playbook")
        if not playbook_cmd:
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": "ansible-playbook binary not found. Install ansible-core or make ansible-playbook available in PATH.",
                "error": "ansible-playbook binary not found",
            }

        temp_dir = tempfile.mkdtemp(prefix="ansible-runner-")
        env = os.environ.copy()
        env["PATH"] = env.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
        env.setdefault("SHELL", "/bin/sh")
        env.setdefault("ANSIBLE_REMOTE_TMP", temp_dir)
        env.setdefault("ANSIBLE_LOCAL_TMP", temp_dir)

        try:
            result = subprocess.run(
                [playbook_cmd, "-i", inventory_path, playbook_path],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except OSError as exc:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(exc),
                "error": str(exc),
            }

        error_message = result.stderr.strip() if result.stderr.strip() else None
        if result.returncode != 0 and not error_message:
            error_message = result.stdout.strip() if result.stdout.strip() else None
        if result.returncode != 0 and not error_message:
            error_message = f"ansible-playbook exited with status {result.returncode}"
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": error_message or "",
        }
    finally:
        if temp_dir:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        try:
            os.remove(inventory_path)
        except Exception:
            pass
        if temp_playbook_path:
            try:
                os.remove(temp_playbook_path)
            except Exception:
                pass


def run_command(servers, command):
    if not servers:
        return {"returncode": 1, "stdout": "", "stderr": "No servers provided to execute command.", "error": "No servers provided"}

    inventory_path = write_inventory(servers)
    try:
        ansible_bin = shutil.which("ansible")
        if not ansible_bin:
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": "ansible binary not found. Install ansible-core or make ansible available in PATH.",
                "error": "ansible binary not found",
            }
        temp_dir = tempfile.mkdtemp(prefix="ansible-runner-")
        try:
            env = os.environ.copy()
            env["PATH"] = env.get("PATH", "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
            env.setdefault("SHELL", "/bin/sh")
            env.setdefault("ANSIBLE_REMOTE_TMP", temp_dir)
            env.setdefault("ANSIBLE_LOCAL_TMP", temp_dir)

            result = subprocess.run(
                [ansible_bin, "-i", inventory_path, "all", "-m", "ansible.builtin.shell", "-a", command],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        error_message = result.stderr.strip() if result.stderr.strip() else None
        if result.returncode != 0 and not error_message:
            error_message = result.stdout.strip() if result.stdout.strip() else None
        if result.returncode != 0 and not error_message:
            error_message = f"ansible command exited with status {result.returncode}"
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": error_message or "",
        }
    except OSError as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "error": str(exc),
        }
    finally:
        try:
            os.remove(inventory_path)
        except OSError:
            pass
