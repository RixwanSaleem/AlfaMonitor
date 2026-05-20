import os
import json
import socket
import threading
import time
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify, send_file
from flask_socketio import emit
from backend.database import engine, SessionLocal
from backend.models import Base, Server, Metric, Alert, PlaybookExecution, SoftwareInstallation, SoftwareTemplate
from backend.auth import authenticate, login_required, create_admin_user
from backend.alerting import send_alert, send_telegram, get_setting
from backend.ansible_manager import run_playbook, run_command
from backend.package_manager import install_package, uninstall_package, list_installed_packages, chocolatey_installed
from backend.crypto import encrypt_text, decrypt_text
from backend.websocket import socketio

Base.metadata.create_all(bind=engine)


def initialize_software_templates():
    """Initialize default software templates if they don't exist."""
    db = SessionLocal()
    try:
        existing_count = db.query(SoftwareTemplate).count()
        if existing_count > 0:
            return
        
        templates = [
            SoftwareTemplate(name="7-Zip", package_name="7zip", description="File archiver", category="utility", version="23.01"),
            SoftwareTemplate(name="Git", package_name="git", description="Version control system", category="development", version="2.41.0"),
            SoftwareTemplate(name="Node.js", package_name="nodejs", description="JavaScript runtime", category="development", version="18.16.1"),
            SoftwareTemplate(name="Python 3", package_name="python3", description="Python programming language", category="development", version="3.11.4"),
            SoftwareTemplate(name=".NET Runtime", package_name="dotnetcore-runtime", description=".NET runtime environment", category="development", version="7.0"),
            SoftwareTemplate(name="Visual Studio Code", package_name="vscode", description="Code editor", category="development", version="1.81.1"),
            SoftwareTemplate(name="Docker Desktop", package_name="docker-desktop", description="Container platform", category="infrastructure", version="4.21.1"),
            SoftwareTemplate(name="OpenVPN", package_name="openvpn", description="VPN client", category="network", version="2.6.4"),
            SoftwareTemplate(name="PuTTY", package_name="putty", description="SSH client", category="network", version="0.78"),
            SoftwareTemplate(name="Notepad++", package_name="notepadplusplus", description="Text editor", category="utility", version="8.5.3"),
            SoftwareTemplate(name="WinRAR", package_name="winrar", description="Archive tool", category="utility", version="6.22"),
            SoftwareTemplate(name="VLC Media Player", package_name="vlc", description="Media player", category="multimedia", version="3.0.18"),
        ]
        
        for template in templates:
            db.add(template)
        
        db.commit()
        print("✓ Software templates initialized")
    except Exception as e:
        print(f"⚠ Failed to initialize software templates: {e}")
    finally:
        db.close()

def parse_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def telegram_notifications_enabled():
    enabled = get_setting("telegram_notifications_enabled")
    if enabled is None or enabled == "":
        return bool(get_setting("telegram_token") and get_setting("telegram_chat_id"))
    return parse_bool(enabled)


def get_telegram_notify_interval():
    raw = get_setting("telegram_notify_interval")
    try:
        interval = int(raw)
        return max(60, interval)
    except Exception:
        return 300


app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")

# Initialize Socket.IO with explicit threading async mode so Engine.IO
# doesn't attempt to load eventlet at import time under Gunicorn.
socketio.init_app(app, async_mode='threading')


def start_periodic_alert_worker(interval_seconds=300):
    def worker():
        while True:
            db = None
            try:
                db = SessionLocal()
                from datetime import timedelta
                servers = db.query(Server).all()
                for server in servers:
                    latest = db.query(Metric).filter(Metric.server_id == server.id).order_by(Metric.created_at.desc()).first()
                    if not latest:
                        continue
                    alerts = []
                    if latest.cpu_percent and latest.cpu_percent > 85:
                        alerts.append(f"High CPU on {server.name}: {latest.cpu_percent}%")
                    if latest.ram_percent and latest.ram_percent > 85:
                        alerts.append(f"High RAM on {server.name}: {latest.ram_percent}%")
                    if latest.disk_percent and latest.disk_percent > 90:
                        alerts.append(f"High disk usage on {server.name}: {latest.disk_percent}%")
                    if alerts:
                        send_alert("\n".join(alerts))
            except Exception:
                app.logger.exception("Periodic alert worker failed")
            finally:
                if db is not None:
                    db.close()
            time.sleep(interval_seconds)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def start_periodic_status_worker():
    def worker():
        while True:
            interval_seconds = get_telegram_notify_interval()
            if telegram_notifications_enabled():
                db = None
                try:
                    db = SessionLocal()
                    from datetime import datetime, timedelta
                    servers = db.query(Server).all()
                    summary_lines = []
                    for server in servers:
                        latest = db.query(Metric).filter(Metric.server_id == server.id).order_by(Metric.created_at.desc()).first()
                        if latest:
                            age = datetime.utcnow() - latest.created_at
                            status = 'online' if age < timedelta(minutes=10) else 'stale'
                            summary_lines.append(
                                f"{server.name} ({server.host}): {status}, CPU {latest.cpu_percent}%, RAM {latest.ram_percent}%, Disk {latest.disk_percent}%"
                            )
                        else:
                            summary_lines.append(f"{server.name} ({server.host}): no metrics yet")
                    if summary_lines:
                        send_telegram("System status update:\n" + "\n".join(summary_lines))
                except Exception:
                    app.logger.exception("Periodic status worker failed")
                finally:
                    if db is not None:
                        db.close()
            time.sleep(interval_seconds)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")
create_admin_user(ADMIN_USER, ADMIN_PASSWORD)
initialize_software_templates()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = authenticate(username, password)
        if user:
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    db = SessionLocal()
    servers = db.query(Server).all()
    db.close()
    return render_template("dashboard.html", servers=servers, username=session.get('username', 'User'))


@app.route("/api/servers", methods=["GET"])
@login_required
def api_servers():
    db = SessionLocal()
    servers = db.query(Server).all()
    payload = [
        {
            "id": s.id,
            "name": s.name,
            "host": s.host,
            "port": s.port,
            "enabled": s.enabled,
        }
        for s in servers
    ]
    db.close()
    return jsonify(payload)


@app.route("/api/server", methods=["POST"])
@login_required
def api_add_server():
    body = request.json or {}
    required = ["name", "host", "username", "password"]
    if any(field not in body for field in required):
        return jsonify({"error": "Missing server details"}), 400
    db = SessionLocal()
    server = Server(
        name=body["name"],
        host=body["host"],
        username=body["username"],
        password=encrypt_text(body["password"]),
        port=int(body.get("port", 22)),
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    db.close()
    return jsonify({"id": server.id, "message": "Server added"})

@app.route("/api/server/<int:server_id>", methods=["PUT"])
@login_required
def api_update_server(server_id):
    body = request.json or {}
    db = SessionLocal()
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        db.close()
        return jsonify({"error": "Server not found"}), 404
    for field in ("name", "host", "username", "password", "port", "enabled"):
        if field in body:
            if field == 'password' and body.get('password'):
                setattr(server, field, encrypt_text(body[field]))
            else:
                setattr(server, field, body[field])
    server.updated_at = datetime.utcnow()
    db.add(server)
    db.commit()
    db.refresh(server)
    db.close()
    return jsonify({"id": server.id, "message": "Server updated"})

@app.route("/api/server/<int:server_id>", methods=["DELETE"])
@login_required
def api_delete_server(server_id):
    db = SessionLocal()
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        db.close()
        return jsonify({"error": "Server not found"}), 404
    db.delete(server)
    db.commit()
    db.close()
    return jsonify({"message": "Server deleted"})

@app.route("/api/server/<int:server_id>/agent-cmd", methods=["GET"])
@login_required
def api_server_agent_cmd(server_id):
    db = SessionLocal()
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        db.close()
        return jsonify({"error": "Server not found"}), 404
    db.close()
    backend_url = request.host_url.strip('/')
    cmd = f"curl -sSL {backend_url}/download/agents.tar.gz | tar xz && python3 agent.py --host {server.host} --username {server.username} --port {server.port}"
    return jsonify({"cmd": cmd})



@app.route('/download/agents.tar.gz')
def download_agents_tar():
    import io
    import tarfile
    base = os.path.join(os.path.dirname(__file__), '..', 'agents')
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for fname in ('agent.py', 'system_info.py', 'config.py'):
            path = os.path.join(base, fname)
            if os.path.exists(path):
                tar.add(path, arcname=fname)
    buf.seek(0)
    return send_file(buf, mimetype='application/gzip', as_attachment=True, download_name='agents.tar.gz')


@app.route("/api/agent/report", methods=["POST"])
def api_agent_report():
    data = request.json or {}
    if not data.get("host"):
        return jsonify({"error": "Invalid report"}), 400
    db = SessionLocal()
    server = db.query(Server).filter(Server.host == data["host"]).first()
    if not server:
        server = Server(
            name=data.get("name", data["host"]),
            host=data["host"],
            username=data.get("username", "agent"),
            password="",
            port=int(data.get("port", 22)),
        )
        db.add(server)
        db.commit()
        db.refresh(server)
    metric = Metric(
        server_id=server.id,
        cpu_percent=int(data.get("cpu_percent", 0)),
        ram_percent=int(data.get("ram_percent", 0)),
        disk_percent=int(data.get("disk_percent", 0)),
        temperature=data.get("temperature", "N/A"),
        services=json.dumps(data.get("services", {})),
    )
    db.add(metric)
    db.commit()
    db.close()

    socketio.emit("metrics", {
        "server": server.host,
        "cpu": metric.cpu_percent,
        "ram": metric.ram_percent,
        "disk": metric.disk_percent,
        "temperature": metric.temperature,
        "services": data.get("services", {}),
        "ram_used_gb": data.get("ram_used_gb"),
        "ram_total_gb": data.get("ram_total_gb"),
        "disk_read": data.get("disk_read"),
        "disk_write": data.get("disk_write"),
        "network_in": data.get("network_in"),
        "network_out": data.get("network_out"),
    }, broadcast=True)

    check_alerts(server, metric)
    return jsonify({"status": "ok"})


def check_alerts(server: Server, metric: Metric):
    alerts = []
    if metric.cpu_percent and metric.cpu_percent > 85:
        alerts.append(f"High CPU on {server.name}: {metric.cpu_percent}%")
    if metric.ram_percent and metric.ram_percent > 85:
        alerts.append(f"High RAM on {server.name}: {metric.ram_percent}%")
    if metric.disk_percent and metric.disk_percent > 90:
        alerts.append(f"High disk usage on {server.name}: {metric.disk_percent}%")

    if alerts:
        db = SessionLocal()
        for message in alerts:
            alert = Alert(server_id=server.id, level="critical", message=message)
            db.add(alert)
            send_alert(message)
        db.commit()
        db.close()


@app.route("/api/alerts", methods=["GET"])
@login_required
def api_alerts():
    db = SessionLocal()
    alerts = db.query(Alert).filter(Alert.active == True).order_by(Alert.created_at.desc()).all()
    payload = [
        {
            "id": a.id,
            "server": a.server.name,
            "level": a.level,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]
    db.close()
    return jsonify(payload)


@app.route("/api/ansible/run", methods=["POST"])
@login_required
def api_ansible_run():
    body = request.json or {}
    playbook_text = (body.get('playbook') or '').strip()
    server_ids = body.get('server_ids', [])

    if not playbook_text:
        return jsonify({"error": "Playbook content is required."}), 400

    db = SessionLocal()
    if server_ids:
        server_objs = db.query(Server).filter(Server.id.in_(server_ids)).all()
    else:
        server_objs = db.query(Server).filter(Server.enabled == True).all()

    if not server_objs:
        db.close()
        return jsonify({"error": "No servers selected or enabled."}), 400

    server_records = [
        {
            "id": s.id,
            "name": s.name,
            "host": s.host,
            "username": s.username,
            "password": s.password,
            "port": s.port,
        }
        for s in server_objs
    ]

    # Create execution record
    execution = PlaybookExecution(
        server_ids=json.dumps([s["id"] for s in server_records]),
        status="running"
    )
    db.add(execution)
    db.commit()
    exec_id = execution.id
    db.close()

    try:
        result = run_playbook(server_records, playbook_text)
    except Exception as exc:
        result = {"returncode": 1, "stdout": "", "stderr": str(exc)}

    db = SessionLocal()
    execution = db.query(PlaybookExecution).filter(PlaybookExecution.id == exec_id).first()
    if execution:
        execution.status = "success" if result.get("returncode") == 0 else "failed"
        execution.return_code = result.get("returncode")
        execution.output = result.get("stdout", "")
        execution.error = result.get("stderr", "")
        execution.completed_at = datetime.utcnow()
        db.add(execution)
        db.commit()
    db.close()
    
    response = {"execution_id": exec_id, **result}
    if result.get("returncode") != 0:
        response["error"] = response.get("error") or response.get("stderr") or response.get("stdout") or "Playbook execution failed"
        return jsonify(response), 400
    return jsonify(response)


@app.route('/api/execute-command', methods=['POST'])
@login_required
def api_execute_command():
    body = request.json or {}
    command = (body.get('command') or '').strip()
    server_ids = body.get('server_ids', [])

    if not command:
        return jsonify({'error': 'Command text is required.'}), 400
    if not isinstance(server_ids, list) or not server_ids:
        return jsonify({'error': 'Select at least one target server.'}), 400

    db = SessionLocal()
    servers = db.query(Server).filter(Server.id.in_(server_ids)).all()
    db.close()
    if not servers:
        return jsonify({'error': 'No matching servers found.'}), 400

    server_records = [
        {
            'id': s.id,
            'name': s.name,
            'host': s.host,
            'username': s.username,
            'password': s.password,
            'port': s.port,
        }
        for s in servers
    ]

    result = run_command(server_records, command)
    if result.get('returncode') != 0:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/executions', methods=['GET'])
@login_required
def api_executions():
    """Get playbook execution history"""
    db = SessionLocal()
    executions = db.query(PlaybookExecution).order_by(PlaybookExecution.created_at.desc()).limit(20).all()
    payload = [
        {
            "id": e.id,
            "status": e.status,
            "return_code": e.return_code,
            "created_at": e.created_at.isoformat(),
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "output": e.output[:200] if e.output else ""
        }
        for e in executions
    ]
    db.close()
    return jsonify(payload)


@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "Connected to monitoring dashboard"})


@app.route('/api/metrics/<int:server_id>', methods=['GET'])
@login_required
def api_metrics(server_id):
    limit = int(request.args.get('limit', 60))
    db = SessionLocal()
    q = db.query(Metric).filter(Metric.server_id == server_id).order_by(Metric.created_at.desc()).limit(limit)
    metrics = q.all()
    db.close()
    metrics = list(reversed(metrics))
    payload = [
        {
            'created_at': m.created_at.isoformat(),
            'cpu': m.cpu_percent,
            'ram': m.ram_percent,
            'disk': m.disk_percent,
            'temperature': m.temperature,
        }
        for m in metrics
    ]
    return jsonify(payload)


@app.route('/api/notifications', methods=['GET', 'POST'])
@login_required
def api_notifications():
    from backend.models import NotificationSetting
    db = SessionLocal()
    if request.method == 'GET':
        settings = db.query(NotificationSetting).all()
        payload = {s.key: s.value for s in settings}
        if 'telegram_notifications_enabled' not in payload:
            payload['telegram_notifications_enabled'] = 'true' if telegram_notifications_enabled() else 'false'
        if 'telegram_notify_interval' not in payload:
            payload['telegram_notify_interval'] = str(get_telegram_notify_interval())
        db.close()
        return jsonify(payload)

    # POST update
    body = request.json or {}
    for k, v in body.items():
        setting = db.query(NotificationSetting).filter(NotificationSetting.key == k).first()
        if setting:
            setting.value = v
            setting.updated_at = datetime.utcnow()
        else:
            setting = NotificationSetting(key=k, value=v)
            db.add(setting)
    db.commit()
    db.close()
    return jsonify({'message': 'updated'})


@app.route('/api/notifications/test', methods=['POST'])
@login_required
def api_notifications_test():
    body = request.json or {}
    message = body.get('message', 'Test alert from monitoring dashboard')
    sent = send_alert(message)
    return jsonify({'sent': sent})


@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def api_users():
    from backend.models import User
    db = SessionLocal()
    if request.method == 'GET':
        users = db.query(User).all()
        payload = [{ 'id': u.id, 'username': u.username, 'is_admin': u.is_admin, 'created_at': u.created_at.isoformat() } for u in users]
        db.close()
        return jsonify(payload)

    body = request.json or {}
    username = body.get('username')
    password = body.get('password')
    is_admin = bool(body.get('is_admin', False))
    if not username or not password:
        db.close()
        return jsonify({'error': 'username and password required'}), 400
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        return jsonify({'error': 'user exists'}), 400
    
    from passlib.hash import bcrypt
    user = User(username=username, password_hash=bcrypt.hash(password), is_admin=is_admin)
    db.add(user)
    db.commit()
    db.close()
    return jsonify({'message': 'user created'})


def is_host_reachable(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

@app.route('/api/server/<int:server_id>/status', methods=['GET'])
@login_required
def api_server_status(server_id):
    """Get server connection status and latest metrics"""
    db = SessionLocal()
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        db.close()
        return jsonify({"error": "Server not found"}), 404
    
    latest_metric = db.query(Metric).filter(Metric.server_id == server_id).order_by(Metric.created_at.desc()).first()
    db.close()
    
    from datetime import timedelta
    if latest_metric:
        time_diff = datetime.utcnow() - latest_metric.created_at
        is_connected = time_diff < timedelta(minutes=10)  # Connected if seen in last 10 min
        return jsonify({
            "connected": is_connected,
            "last_seen": latest_metric.created_at.isoformat(),
            "cpu": latest_metric.cpu_percent,
            "ram": latest_metric.ram_percent,
            "disk": latest_metric.disk_percent,
            "temperature": latest_metric.temperature
        })

    # Fallback to network reachability if no recent metrics are available
    reachable = is_host_reachable(server.host, server.port)
    return jsonify({
        "connected": reachable,
        "last_seen": None,
        "cpu": 0,
        "ram": 0,
        "disk": 0,
        "temperature": "N/A"
    })


@app.route('/api/servers/latest-metrics', methods=['GET'])
@login_required
def api_servers_latest_metrics():
    """Get latest metrics for all servers for live dashboard"""
    db = SessionLocal()
    servers = db.query(Server).all()
    payload = []
    
    from datetime import datetime, timedelta
    for server in servers:
        latest = db.query(Metric).filter(Metric.server_id == server.id).order_by(Metric.created_at.desc()).first()
        if latest:
            time_diff = datetime.utcnow() - latest.created_at
            is_connected = time_diff < timedelta(minutes=10)
            payload.append({
                "id": server.id,
                "name": server.name,
                "host": server.host,
                "connected": is_connected,
                "cpu": latest.cpu_percent,
                "ram": latest.ram_percent,
                "disk": latest.disk_percent,
                "temperature": latest.temperature
            })
        else:
            reachable = is_host_reachable(server.host, server.port)
            payload.append({
                "id": server.id,
                "name": server.name,
                "host": server.host,
                "connected": reachable,
                "cpu": None,
                "ram": None,
                "disk": None,
                "temperature": "N/A"
            })
    
    db.close()
    return jsonify(payload)


@app.route('/api/executions', methods=['DELETE'])
@login_required
def api_clear_executions():
    db = SessionLocal()
    db.query(PlaybookExecution).delete()
    db.commit()
    db.close()
    return jsonify({'message': 'Execution history cleared'})


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    from backend.models import User
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return jsonify({'error': 'not found'}), 404
    db.delete(user)
    db.commit()
    db.close()
    return jsonify({'message': 'deleted'})


@app.route('/api/software/templates', methods=['GET'])
@login_required
def api_software_templates():
    db = SessionLocal()
    templates = db.query(SoftwareTemplate).all()
    payload = [
        {
            "id": t.id,
            "name": t.name,
            "package_name": t.package_name,
            "description": t.description,
            "category": t.category,
            "version": t.version,
        }
        for t in templates
    ]
    db.close()
    return jsonify(payload)


@app.route('/api/software/install', methods=['POST'])
@login_required
def api_software_install():
    body = request.json or {}
    server_ids = body.get('server_ids', [])
    package_name = (body.get('package_name') or '').strip()
    package_version = (body.get('package_version') or '').strip()

    if not package_name:
        return jsonify({"error": "Package name is required"}), 400

    db = SessionLocal()
    if server_ids:
        servers = db.query(Server).filter(Server.id.in_(server_ids)).all()
    else:
        servers = db.query(Server).filter(Server.enabled == True).all()

    if not servers:
        db.close()
        return jsonify({"error": "No servers selected or enabled"}), 400

    server_records = [
        {
            "id": s.id,
            "name": s.name,
            "host": s.host,
            "username": s.username,
            "password": s.password,
            "port": s.port,
        }
        for s in servers
    ]

    installation = SoftwareInstallation(
        server_ids=json.dumps([s["id"] for s in server_records]),
        package_name=package_name,
        package_version=package_version if package_version else None,
        status="running"
    )
    db.add(installation)
    db.commit()
    install_id = installation.id
    db.close()

    def run_installation():
        try:
            result = install_package(server_records, package_name, package_version if package_version else None)
        except Exception as exc:
            result = {"returncode": 1, "stdout": "", "stderr": str(exc), "error": str(exc)}

        db = SessionLocal()
        installation = db.query(SoftwareInstallation).filter(SoftwareInstallation.id == install_id).first()
        if installation:
            installation.status = "success" if result.get("returncode") == 0 else "failed"
            installation.return_code = result.get("returncode")
            installation.output = result.get("stdout", "")
            installation.error = result.get("stderr", "") or result.get("error", "")
            installation.completed_at = datetime.utcnow()
            db.add(installation)
            db.commit()
        db.close()

        socketio.emit('software_installation_complete', {
            'id': install_id,
            'status': installation.status if installation else 'failed',
            'package': package_name,
        }, namespace='/')

    thread = threading.Thread(target=run_installation, daemon=True)
    thread.start()

    return jsonify({"id": install_id, "status": "running", "message": f"Installing {package_name}..."})


@app.route('/api/software/status/<int:job_id>', methods=['GET'])
@login_required
def api_software_status(job_id):
    db = SessionLocal()
    installation = db.query(SoftwareInstallation).filter(SoftwareInstallation.id == job_id).first()
    if not installation:
        db.close()
        return jsonify({"error": "Installation job not found"}), 404

    payload = {
        "id": installation.id,
        "package_name": installation.package_name,
        "status": installation.status,
        "output": installation.output,
        "error": installation.error,
        "return_code": installation.return_code,
        "created_at": installation.created_at.isoformat() if installation.created_at else None,
        "completed_at": installation.completed_at.isoformat() if installation.completed_at else None,
    }
    db.close()
    return jsonify(payload)


@app.route('/api/software/history', methods=['GET'])
@login_required
def api_software_history():
    db = SessionLocal()
    installations = db.query(SoftwareInstallation).order_by(SoftwareInstallation.created_at.desc()).limit(50).all()
    payload = [
        {
            "id": i.id,
            "package_name": i.package_name,
            "package_version": i.package_version,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in installations
    ]
    db.close()
    return jsonify(payload)


@app.route('/api/software/installed/<int:server_id>', methods=['GET'])
@login_required
def api_software_installed(server_id):
    db = SessionLocal()
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        db.close()
        return jsonify({"error": "Server not found"}), 404

    server_record = {
        "id": server.id,
        "name": server.name,
        "host": server.host,
        "username": server.username,
        "password": server.password,
        "port": server.port,
    }

    result = list_installed_packages([server_record])
    db.close()

    return jsonify({
        "server_id": server_id,
        "server_name": server.name,
        "packages": result.get("stdout", ""),
        "error": result.get("error", ""),
        "returncode": result.get("returncode"),
    })


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") != "false":
        start_periodic_alert_worker()
        start_periodic_status_worker()
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
