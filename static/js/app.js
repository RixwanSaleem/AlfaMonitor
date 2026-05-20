console.log('Dashboard app.js loaded');
const socket = io();

// Helper that always sends same-origin credentials and handles 401 redirects
async function apiFetch(path, opts = {}) {
  opts = Object.assign({}, opts);
  opts.credentials = opts.credentials || 'same-origin';
  if (opts.body && typeof opts.body !== 'string') {
    opts.body = JSON.stringify(opts.body);
    opts.headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  }
  const res = await fetch(path, opts);
  if (res.status === 401) {
    window.location = '/login';
    throw new Error('Unauthorized');
  }
  return res;
}

socket.on("connect", () => {
  console.log("Connected to dashboard socket");
});

socket.on("metrics", (payload) => {
  const row = document.querySelector(`tr[data-server-host="${payload.server}"]`);
  if (row) {
    const indicator = row.querySelector('.status-indicator');
    const statusText = row.querySelector('.status-text');
    if (indicator) {
      indicator.classList.remove('disconnected');
      indicator.classList.add('connected');
      indicator.title = `Connected - CPU: ${payload.cpu}% RAM: ${payload.ram}%`;
    }
    if (statusText) {
      statusText.textContent = 'Connected';
    }
  }

  const cpuValue = document.getElementById('cpu-value');
  const cpuProgress = document.getElementById('cpu-progress');
  const cpuStatusLabel = document.getElementById('cpu-status-label');
  const cpuUtilLabel = document.getElementById('cpu-util-label');
  const ramValue = document.getElementById('ram-value');
  const ramUsed = document.getElementById('ram-used-value');
  const ramTotal = document.getElementById('ram-total-value');
  const ramProgress = document.getElementById('ram-progress');
  const diskValue = document.getElementById('disk-value');
  const diskRead = document.getElementById('disk-read-value');
  const diskWrite = document.getElementById('disk-write-value');
  const netUsage = document.getElementById('net-usage-value');
  const netIn = document.getElementById('net-in-value');
  const netOut = document.getElementById('net-out-value');

  const cpuCard = document.getElementById('cpu-card');
  const ramCard = document.getElementById('ram-card');
  const diskCard = document.getElementById('disk-card');
  const networkCard = document.getElementById('network-card');

  const applyStatus = (card, value) => {
    if (!card) return;
    card.classList.remove('normal', 'warning', 'critical');
    if (value >= 90) card.classList.add('critical');
    else if (value >= 70) card.classList.add('warning');
    else card.classList.add('normal');
  };

  const metricLevelText = (value) => {
    if (value >= 90) return 'Critical';
    if (value >= 70) return 'Warning';
    if (value > 0) return 'Normal';
    return 'Idle';
  };

  if (cpuValue) cpuValue.textContent = `${payload.cpu ?? '--'}%`;
  if (cpuStatusLabel) cpuStatusLabel.textContent = metricLevelText(payload.cpu);
  if (cpuUtilLabel) cpuUtilLabel.textContent = `${payload.cpu ?? '--'}%`;
  if (cpuProgress) cpuProgress.style.width = `${payload.cpu ?? 0}%`;
  if (ramValue) ramValue.textContent = `${payload.ram ?? '--'}%`;
  if (ramProgress) ramProgress.style.width = `${payload.ram ?? 0}%`;
  if (ramUsed) ramUsed.textContent = `${payload.ram_used ?? '--'} GB`;
  if (ramTotal) ramTotal.textContent = `${payload.ram_total ?? '--'} GB`;
  if (diskValue) diskValue.textContent = `${payload.disk ?? '--'}%`;
  if (diskRead) diskRead.textContent = payload.disk_read || '--';
  if (diskWrite) diskWrite.textContent = payload.disk_write || '--';
  if (netUsage) netUsage.textContent = `${payload.network_in || '--'} / ${payload.network_out || '--'}`;
  if (netIn) netIn.textContent = payload.network_in || '--';
  if (netOut) netOut.textContent = payload.network_out || '--';

  applyStatus(cpuCard, payload.cpu);
  applyStatus(ramCard, payload.ram);
  applyStatus(diskCard, payload.disk);
  const networkPercent = payload.network_percent ?? Math.max(payload.network_utilization || 0, 0);
  applyStatus(networkCard, networkPercent);

  const summary = document.getElementById('live-status-summary');
  if (summary) {
    summary.textContent = `Live update from ${payload.server}`;
  }

  addAlertIfNeeded(payload);
});

async function fetchAlerts() {
  const response = await apiFetch('/api/alerts');
  if (!response.ok) return;
  const alerts = await response.json();
  const list = document.getElementById('alerts-list');
  if (!alerts.length) {
    list.innerHTML = '<div class="alert-item">No active alerts.</div>';
    return;
  }
  list.innerHTML = alerts.map(alert => `
    <div class="alert-item">
      <strong>${alert.server}</strong>
      <p>${alert.message}</p>
      <small>${new Date(alert.created_at).toLocaleString()}</small>
    </div>
  `).join('');
}

function addAlertIfNeeded(payload) {
  const warnings = [];
  if (payload.cpu > 85) warnings.push(`CPU ${payload.cpu}%`);
  if (payload.ram > 85) warnings.push(`RAM ${payload.ram}%`);
  if (payload.disk > 90) warnings.push(`Disk ${payload.disk}%`);
  if (warnings.length) {
    const list = document.getElementById('alerts-list');
    const node = document.createElement('div');
    node.className = 'alert-item';
    node.innerHTML = `<strong>${payload.server}</strong><p>${warnings.join(', ')}</p><small>Now</small>`;
    list.prepend(node);
  }
}

window.addEventListener('load', () => {
  fetchAlerts();
  fetchServers();
  loadNotificationSettings();
  loadUsers();
  loadLiveMetrics();
  loadExecutionHistory();
  
  // Refresh metrics every 30 seconds
  setInterval(loadLiveMetrics, 2500);
  setInterval(loadExecutionHistory, 60000);
  
  // Display current user - properly get from template
  const userDisplayEl = document.getElementById('user-display');
  const usernameFromBackend = document.body.getAttribute('data-username') || '{{ username }}';
  if (userDisplayEl && usernameFromBackend && usernameFromBackend !== '{{ username }}') {
    userDisplayEl.innerHTML = `👤 <strong>${usernameFromBackend}</strong>`;
  }
  
  document.getElementById('refresh-server-list')?.addEventListener('click', () => fetchServers());

  function hideAllLazyPanels() {
    document.querySelectorAll('.lazy-panel').forEach(panel => {
      panel.classList.add('hidden');
      panel.setAttribute('aria-hidden', 'true');
    });
  }

  function openDashboardPanel(panelId) {
    hideAllLazyPanels();
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.classList.remove('hidden');
    panel.setAttribute('aria-hidden', 'false');
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (panelId === 'performance-panel') {
      document.getElementById('metrics-server-select')?.focus();
    }
    if (panelId === 'playbook-panel') {
      const editor = document.getElementById('playbook-editor');
      if (editor) editor.focus();
    }
  }

  document.querySelectorAll('.dashboard-action-btn').forEach(btn => {
    btn.addEventListener('click', () => openDashboardPanel(btn.dataset.panel));
  });
  document.getElementById('close-performance')?.addEventListener('click', hideAllLazyPanels);
  document.getElementById('close-playbook')?.addEventListener('click', hideAllLazyPanels);
  document.getElementById('close-services')?.addEventListener('click', hideAllLazyPanels);

  const inactivityTimeoutMs = 5 * 60 * 1000;
  let inactivityTimer;
  let logoutScheduler;

  function showToast(message, duration = 1800) {
    const toast = document.getElementById('inactivity-toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    toast.classList.remove('hidden');
    clearTimeout(logoutScheduler);
    logoutScheduler = setTimeout(() => {
      toast.classList.remove('show');
      toast.classList.add('hidden');
    }, duration);
  }

  function performAutoLogout() {
    showToast('Logging out due to inactivity...', 1600);
    setTimeout(() => {
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/logout';
    }, 1600);
  }

  const resetInactivityTimer = () => {
    if (inactivityTimer) clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(performAutoLogout, inactivityTimeoutMs);
  };
  ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(eventName => {
    window.addEventListener(eventName, resetInactivityTimer);
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      resetInactivityTimer();
    }
  });
  resetInactivityTimer();

  // Metrics history button
  document.getElementById('load-metrics')?.addEventListener('click', async () => {
    const sel = document.getElementById('metrics-server-select');
    if (!sel || !sel.value) {
      alert('Please select a server first');
      return;
    }
    const container = document.getElementById('charts-container');
    if (!container) return;
    container.classList.remove('hidden');
    if (container.style.display === 'grid' || container.style.display === 'block') {
      container.style.display = 'none';
      return;
    }
    container.style.display = 'grid';
    await loadMetrics(sel.value);
  });

  document.getElementById('run-playbook')?.addEventListener('click', async () => {
    const checkboxes = Array.from(document.querySelectorAll('.server-select:checked'));
    if (!checkboxes.length) { alert('Select at least one server'); return; }
    const ids = checkboxes.map(cb => parseInt(cb.value, 10));
    const playbookText = document.getElementById('playbook-editor')?.value.trim();
    if (!playbookText) {
      alert('Please enter a playbook before running.');
      return;
    }
    try {
      const res = await apiFetch('/api/ansible/run', { method: 'POST', body: { server_ids: ids, playbook: playbookText } });
      const data = await (res.headers.get('Content-Type')?.includes('application/json') ? res.json() : Promise.resolve({ stdout: '', stderr: await res.text() }));
      if (!res.ok) {
        console.error('Playbook run failed', data);
        const errMsg = data.error || data.stderr || data.stdout || res.statusText || 'unknown error';
        alert('Playbook failed: ' + errMsg);
      } else {
        alert('Playbook requested, return code: ' + (data.returncode ?? 'n/a'));
      }
      loadExecutionHistory();
    } catch (err) {
      console.error(err);
      alert('Failed to run playbook: ' + (err.message || err));
    }
  });

function updateCommandStatus(status, timeText) {
      const statusTextEl = document.getElementById('command-status-text');
      const statusTimeEl = document.getElementById('command-status-time');
      if (statusTextEl) statusTextEl.textContent = status;
      if (statusTimeEl) statusTimeEl.textContent = timeText;
    }

    document.getElementById('run-command')?.addEventListener('click', async () => {
      const commandField = document.getElementById('command-input');
      const commandOutput = document.getElementById('command-output');
      const commandSelect = document.getElementById('command-server-select');
      if (!commandField || !commandOutput || !commandSelect) return;

      const command = commandField.value.trim();
      const selectedIds = Array.from(commandSelect.selectedOptions).map(o => parseInt(o.value, 10));
      if (!command) {
        alert('Please enter a command to run.');
        return;
      }
      if (!selectedIds.length) {
        alert('Select at least one server from the target list.');
        return;
      }

      const startTime = new Date();
      updateCommandStatus('Running', startTime.toLocaleString());
      commandOutput.textContent = 'Running command...';
      try {
        const res = await apiFetch('/api/execute-command', { method: 'POST', body: { server_ids: selectedIds, command } });
        const data = await res.json();
        const outputText = [];
        if (data.stdout) outputText.push(data.stdout.trim());
        if (data.stderr) outputText.push(data.stderr.trim());
        if (data.error) outputText.push(`Error: ${data.error}`);
        if (!outputText.length) outputText.push('Command executed with no output.');
        commandOutput.textContent = outputText.join('\n\n');
        updateCommandStatus(res.ok ? 'Success' : 'Failed', new Date().toLocaleString());
        if (!res.ok) {
          alert('Command execution failed. See output for details.');
        }
      } catch (err) {
        console.error(err);
        commandOutput.textContent = 'Failed to execute command: ' + (err.message || err);
        updateCommandStatus('Failed', new Date().toLocaleString());
    }
  });

  // Clear alerts button
  document.getElementById('clear-alerts')?.addEventListener('click', async () => {
    if (!confirm('Clear all alerts?')) return;
    alert('Feature coming soon');
  });

  // Add server form handlers
  const openBtn = document.getElementById('open-add-server');
  const addFormWrap = document.getElementById('add-server-form');
  const cancelBtn = document.getElementById('cancel-add-server');
  const serverForm = document.getElementById('server-form');

  openBtn?.addEventListener('click', () => {
    addFormWrap?.classList.remove('hidden');
    openBtn.style.display = 'none';
  });

  cancelBtn?.addEventListener('click', () => {
    addFormWrap?.classList.add('hidden');
    openBtn.style.display = 'inline-block';
    serverForm?.reset();
  });

  serverForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(serverForm);
    const body = {};
    for (const [k, v] of formData.entries()) body[k] = v;
    try {
      const res = await apiFetch('/api/server', { method: 'POST', body });
      if (!res.ok) {
        const err = await res.json();
        alert('Failed to add server: ' + (err.error || res.statusText));
        return;
      }
      const data = await res.json();
      serverForm.reset();
      addFormWrap.classList.add('hidden');
      openBtn.style.display = 'inline-block';
      fetchServers();
      alert('Server added successfully');
    } catch (err) {
      console.error(err);
      alert('Network error adding server');
    }
  });

  initDashboardTabs();
});

async function fetchServers() {
  try {
    const res = await apiFetch('/api/servers');
    if (!res.ok) return;
    const servers = await res.json();
    const tbody = document.getElementById('server-table-body');
    
    if (!servers || servers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: rgba(248, 250, 253, 0.5);">No servers added yet</td></tr>';
      return;
    }
    
    const serverRows = servers.map(s => {
      return `<tr data-server-id="${s.id}" data-server-host="${s.host}">
        <td><input type="checkbox" class="server-select" value="${s.id}" /></td>
        <td>${s.name}</td>
        <td>${s.host}</td>
        <td>${s.port}</td>
        <td>
          <span class="status-indicator disconnected" title="Checking..."></span>
          <span class="status-text">${s.enabled ? 'Checking...' : 'Disabled'}</span>
        </td>
        <td style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button onclick="editServer(${s.id})" style="font-size: 0.75rem; padding: 0.3rem 0.5rem;">✏️ Edit</button>
          <button onclick="deleteServer(${s.id})" style="font-size: 0.75rem; padding: 0.3rem 0.5rem;">🗑️ Del</button>
          <button onclick="showAgentCmd(${s.id})" style="font-size: 0.75rem; padding: 0.3rem 0.5rem;">⚙️ Agent</button>
        </td>
      </tr>`;
    }).join('');
    
    tbody.innerHTML = serverRows;
    
    servers.forEach(async (s) => {
      try {
        const statusRes = await apiFetch(`/api/server/${s.id}/status`);
        if (statusRes.ok) {
          const status = await statusRes.json();
          // Verify row exists and still has the same server ID to prevent race conditions
          const row = document.querySelector(`tr[data-server-id="${s.id}"]`);
          if (row && row.getAttribute('data-server-id') === String(s.id)) {
            const indicator = row.querySelector('.status-indicator');
            const statusText = row.querySelector('.status-text');
            if (status.connected) {
              if (indicator) {
                indicator.classList.remove('disconnected');
                indicator.classList.add('connected');
                indicator.title = `Connected - CPU: ${status.cpu}% RAM: ${status.ram}%`;
              }
              if (statusText) statusText.textContent = 'Connected';
            } else {
              if (indicator) {
                indicator.classList.remove('connected');
                indicator.classList.add('disconnected');
                indicator.title = 'No recent data';
              }
              if (statusText) statusText.textContent = 'No recent data';
            }
          }
        }
      } catch (e) {
        console.error('Error checking server status:', e);
      }
    });
    
    const select = document.getElementById('metrics-server-select');
    if (select) {
      select.innerHTML = '<option value="" disabled selected>Select server</option>' +
        servers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    }
    const commandSelect = document.getElementById('command-server-select');
    if (commandSelect) {
      commandSelect.innerHTML = servers.map(s => `<option value="${s.id}">${s.name} (${s.host})</option>`).join('');
    }
  } catch (err) {
    console.error('Failed to fetch servers', err);
  }
}

window.editServer = async function(id) {
  try {
    const name = prompt('Name:');
    if (name === null) return;
    const host = prompt('Host/IP:');
    if (host === null) return;
    const username = prompt('SSH Username:');
    if (username === null) return;
    const password = prompt('Password (leave blank to keep):');
    const port = prompt('Port:', '22');
    const enabled = confirm('Enable this server?');
    const body = { name, host, username, port: parseInt(port, 10), enabled };
    if (password) body.password = password;
    const res = await apiFetch(`/api/server/${id}`, { method: 'PUT', body });
    if (!res.ok) { alert('Failed to update server'); return; }
    alert('Server updated');
    fetchServers();
  } catch (err) { console.error(err); alert('Error updating server'); }
}

function initDashboardTabs() {
  const buttons = Array.from(document.querySelectorAll('.tab-btn'));
  const panes = Array.from(document.querySelectorAll('.tab-pane'));
  buttons.forEach(button => {
    button.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));
      button.classList.add('active');
      const target = document.getElementById(`tab-${button.dataset.tab}`);
      if (target) target.classList.add('active');
    });
  });
}

window.deleteServer = async function(id) {
  if (!confirm('Delete this server?')) return;
  try {
    const res = await apiFetch(`/api/server/${id}`, { method: 'DELETE' });
    if (!res.ok) { alert('Failed to delete server'); return; }
    alert('Server deleted');
    fetchServers();
  } catch (err) { console.error(err); alert('Error deleting server'); }
}

window.showAgentCmd = async function(id) {
  try {
    const res = await apiFetch(`/api/server/${id}/agent-cmd`);
    if (!res.ok) { alert('Failed to get agent command'); return; }
    const data = await res.json();
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(data.cmd);
      alert('Agent install command copied to clipboard');
    } else {
      prompt('Agent command (copy):', data.cmd);
    }
  } catch (err) { console.error(err); alert('Error fetching agent command'); }
}

// Charts: CPU, RAM, Disk
let cpuChart = null, ramChart = null, diskChart = null;
let chartsVisible = false;


async function loadMetrics(serverId) {
  try {
    console.log('Loading metrics for server:', serverId);
    const res = await apiFetch(`/api/metrics/${serverId}?limit=120`);
    if (!res.ok) {
      alert('Error loading metrics: ' + res.statusText);
      return;
    }
    const points = await res.json();
    console.log('Received metrics:', points.length);
    if (!points || points.length === 0) {
      const container = document.getElementById('charts-container');
      if (container) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: rgba(248, 250, 253, 0.5); border: 1px dashed rgba(88, 166, 255, 0.3); border-radius: 10px;"><p style="margin: 0;"><strong>No metrics available yet</strong></p><p style="margin: 0.5rem 0 0; font-size: 0.85rem;">Deploy monitoring agents on your servers to start collecting metrics. Use the Agent button in the server table.</p></div>';
        container.style.display = 'grid';
      }
      return;
    }
    const labels = points.map(p => new Date(p.created_at).toLocaleTimeString());
    const cpuData = points.map(p => p.cpu ?? 0);
    const ramData = points.map(p => p.ram ?? 0);
    const diskData = points.map(p => p.disk ?? 0);

    const cpuEl = document.getElementById('cpuChart');
    const ramEl = document.getElementById('ramChart');
    const diskEl = document.getElementById('diskChart');
    
    if (!cpuEl || !ramEl || !diskEl) {
      console.error('Canvas elements not found');
      return;
    }

    const cpuCtx = cpuEl.getContext('2d');
    const ramCtx = ramEl.getContext('2d');
    const diskCtx = diskEl.getContext('2d');

    const opts = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } };

    if (cpuChart) cpuChart.destroy();
    cpuChart = new Chart(cpuCtx, { type: 'line', data: { labels, datasets: [{ label: 'CPU %', data: cpuData, borderColor: '#ff6384', backgroundColor: 'rgba(255,99,132,0.08)', fill: true }] }, options: opts });

    if (ramChart) ramChart.destroy();
    ramChart = new Chart(ramCtx, { type: 'line', data: { labels, datasets: [{ label: 'RAM %', data: ramData, borderColor: '#36a2eb', backgroundColor: 'rgba(54,162,235,0.08)', fill: true }] }, options: opts });

    if (diskChart) diskChart.destroy();
    diskChart = new Chart(diskCtx, { type: 'line', data: { labels, datasets: [{ label: 'Disk %', data: diskData, borderColor: '#f7c948', backgroundColor: 'rgba(247,201,72,0.08)', fill: true }] }, options: opts });
    console.log('Charts rendered');
  } catch (err) { console.error('Failed to load metrics', err); alert('Error loading metrics: ' + err.message); }
}

// Notification settings handlers
async function loadNotificationSettings() {
  try {
    const res = await apiFetch('/api/notifications');
    if (!res.ok) return;
    const s = await res.json();
    document.getElementById('notif-telegram-enabled').checked = s.telegram_notifications_enabled === 'true';
    document.getElementById('notif-telegram-token').value = s.telegram_token || '';
    document.getElementById('notif-telegram-chat').value = s.telegram_chat_id || '';
    document.getElementById('notif-telegram-interval').value = s.telegram_notify_interval || '300';
    document.getElementById('notif-discord-webhook').value = s.discord_webhook_url || '';
  } catch (err) { console.error('Failed to load notifications', err); }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('save-notif')?.addEventListener('click', async () => {
    const body = {
      telegram_notifications_enabled: document.getElementById('notif-telegram-enabled').checked ? 'true' : 'false',
      telegram_token: document.getElementById('notif-telegram-token').value.trim(),
      telegram_chat_id: document.getElementById('notif-telegram-chat').value.trim(),
      telegram_notify_interval: document.getElementById('notif-telegram-interval').value.trim() || '300',
      discord_webhook_url: document.getElementById('notif-discord-webhook').value.trim(),
    };
    try {
      const res = await apiFetch('/api/notifications', { method: 'POST', body });
      if (!res.ok) { alert('Failed to save settings'); return; }
      alert('Settings saved');
    } catch (err) { console.error(err); alert('Error saving settings'); }
  });

  document.getElementById('test-notif')?.addEventListener('click', async () => {
    const message = prompt('Test message:', 'This is a test alert from the dashboard');
    if (message === null) return;
    try {
      const res = await apiFetch('/api/notifications/test', { method: 'POST', body: { message } });
      const data = await res.json();
      alert('Sent: ' + data.sent);
    } catch (err) { console.error(err); alert('Error sending test'); }
  });

  document.getElementById('create-user')?.addEventListener('click', async () => {
    const username = document.getElementById('new-user-username').value.trim();
    const password = document.getElementById('new-user-password').value;
    if (!username || !password) { alert('Provide username and password'); return; }
    try {
      const res = await apiFetch('/api/users', { method: 'POST', body: { username, password } });
      if (!res.ok) { const e = await res.json(); alert('Failed: ' + (e.error || 'error')); return; }
      document.getElementById('new-user-username').value=''; document.getElementById('new-user-password').value='';
      loadUsers();
      alert('User created');
    } catch (err) { console.error(err); alert('Error creating user'); }
  });

  document.getElementById('clear-executions')?.addEventListener('click', async () => {
    if (!confirm('Clear playbook execution history?')) return;
    try {
      const res = await apiFetch('/api/executions', { method: 'DELETE' });
      if (!res.ok) { alert('Failed to clear history'); return; }
      await loadExecutionHistory();
      alert('Playbook execution history cleared');
    } catch (err) {
      console.error(err);
      alert('Error clearing history');
    }
  });
});

// load notif settings on page load
// Users management
async function loadUsers() {
  try {
    const res = await apiFetch('/api/users');
    if (!res.ok) return;
    const users = await res.json();
    const container = document.getElementById('users-list');
    if (!users.length) { container.innerHTML = '<div>No users</div>'; return; }
    container.innerHTML = users.map(u => `<div style="display:flex;justify-content:space-between;align-items:center;padding:0.5rem;border-radius:8px;background:rgba(255,255,255,0.02);margin-bottom:0.4rem;"><div>${u.username} <small style="opacity:0.7">${u.is_admin? 'admin':''}</small></div><div><button onclick="deleteUser(${u.id})">Delete</button></div></div>`).join('');
  } catch (err) { console.error(err); }
}

window.deleteUser = async function(id) {
  if (!confirm('Delete user?')) return;
  try {
    const res = await apiFetch(`/api/users/${id}`, { method: 'DELETE' });
    if (!res.ok) { alert('Failed to delete'); return; }
    loadUsers();
  } catch (err) { console.error(err); alert('Error deleting user'); }
}

// Command Execution
window.runCommand = function(serverId) {
  const command = prompt('Enter command to run on server:');
  if (!command) return;
  alert('Command execution feature coming soon! For now, SSH into the server.\n\nCommand would run: ' + command);
};

// Load execution history
async function loadExecutionHistory() {
  try {
    const res = await apiFetch('/api/executions');
    if (!res.ok) return;
    const executions = await res.json();
    const container = document.getElementById('execution-history');
    if (!container) return;
    
    if (!executions.length) {
      container.innerHTML = '<div style="text-align: center; padding: 1rem; color: rgba(248, 250, 253, 0.5);">No executions yet</div>';
      return;
    }
    
    container.innerHTML = executions.map(e => {
      const statusColor = e.status === 'success' ? '#4caf50' : e.status === 'failed' ? '#ff6384' : '#ff9800';
      return `<div style="padding: 0.75rem; border-radius: 8px; background: rgba(255,255,255,0.02); border-left: 4px solid ${statusColor}; margin-bottom: 0.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: ${statusColor};">${e.status.toUpperCase()}</strong>
            <small style="display: block; color: rgba(248, 250, 253, 0.5);">RC: ${e.return_code ?? 'N/A'}</small>
          </div>
          <small style="color: rgba(248, 250, 253, 0.5);">${new Date(e.created_at).toLocaleString()}</small>
        </div>
        ${e.output ? `<small style="display: block; margin-top: 0.5rem; color: rgba(248, 250, 253, 0.6); font-family: monospace; background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px;">${e.output}</small>` : ''}
      </div>`;
    }).join('');
  } catch (err) { console.error('Failed to load execution history', err); }
}

// Load live metrics from all servers
async function loadLiveMetrics() {
  try {
    const res = await apiFetch('/api/servers/latest-metrics');
    if (!res.ok) return;
    const metrics = await res.json();
    const cpuEl = document.getElementById('cpu-value');
    const ramEl = document.getElementById('ram-value');
    const diskEl = document.getElementById('disk-value');
    const tempEl = document.getElementById('temp-value');
    const summary = document.getElementById('live-status-summary');

    if (!metrics || metrics.length === 0) {
      if (cpuEl) cpuEl.textContent = '--%';
      if (ramEl) ramEl.textContent = '--%';
      if (diskEl) diskEl.textContent = '--%';
      if (tempEl) tempEl.textContent = '--';
      if (summary) summary.innerHTML = '<span style="color: #ff9800;">⚠️ No servers added yet. Configure servers to start monitoring.</span>';
      return;
    }

    const latestConnected = metrics.find(m => m.connected && m.cpu !== null && m.ram !== null && m.disk !== null);
    const latest = latestConnected || metrics.find(m => m.cpu !== null || m.ram !== null || m.disk !== null) || metrics[0];

    const formatValue = (value) => (value !== null && value !== undefined ? `${value}%` : '--%');
    if (cpuEl) cpuEl.textContent = formatValue(latest.cpu);
    if (ramEl) ramEl.textContent = formatValue(latest.ram);
    if (diskEl) diskEl.textContent = formatValue(latest.disk);
    if (tempEl) tempEl.textContent = latest.temperature && latest.temperature !== 'N/A' ? latest.temperature : '--';

    const ramUsedEl = document.getElementById('ram-used-value');
    const ramTotalEl = document.getElementById('ram-total-value');
    const ramProgressEl = document.getElementById('ram-progress');
    const diskReadEl = document.getElementById('disk-read-value');
    const diskWriteEl = document.getElementById('disk-write-value');
    const netUsageEl = document.getElementById('net-usage-value');
    const netInEl = document.getElementById('net-in-value');
    const netOutEl = document.getElementById('net-out-value');

    if (ramUsedEl && ramTotalEl) {
      ramUsedEl.textContent = latest.ram_used_gb ? `${latest.ram_used_gb} GB` : '-- GB';
      ramTotalEl.textContent = latest.ram_total_gb ? `${latest.ram_total_gb} GB` : '-- GB';
    }
    if (ramProgressEl) ramProgressEl.style.width = `${latest.ram ?? 0}%`;
    if (diskReadEl) diskReadEl.textContent = latest.disk_read || '--';
    if (diskWriteEl) diskWriteEl.textContent = latest.disk_write || '--';
    if (netUsageEl) netUsageEl.textContent = `${latest.network_in || '--'} / ${latest.network_out || '--'}`;
    if (netInEl) netInEl.textContent = latest.network_in || '--';
    if (netOutEl) netOutEl.textContent = latest.network_out || '--';

    if (summary) {
      const connectedCount = metrics.filter(m => m.connected).length;
      const totalCount = metrics.length;
      const hasMetrics = metrics.some(m => m.cpu !== null || m.ram !== null || m.disk !== null);
      
      if (!hasMetrics) {
        summary.innerHTML = `<span style="color: #ffa500;">⏳ ${connectedCount} connected server${connectedCount === 1 ? '' : 's'} detected. Waiting for agents to send metrics...</span>`;
      } else {
        summary.innerHTML = `<span style="color: #4caf50;">✓ ${connectedCount} connected server${connectedCount === 1 ? '' : 's'} out of ${totalCount}.</span>`;
      }
    }
  } catch (err) {
    console.error('Failed to load live metrics', err);
  }
}

async function loadSoftwareTemplates() {
  try {
    const response = await fetch('/api/software/templates');
    const templates = await response.json();
    const container = document.getElementById('software-templates-list');
    if (!container) return;

    if (templates.length === 0) {
      container.innerHTML = '<div style="text-align:center; color:#8b949e;">No templates available</div>';
      return;
    }

    container.innerHTML = templates.map(t => `
      <button 
        class="control-btn" 
        style="background:#38bdf8; padding:6px 10px; font-size:0.8rem; text-align:left; cursor:pointer;"
        onclick="quickInstallTemplate('${t.package_name}', '${t.name}')"
        title="${t.description || ''}"
      >
        ${t.name} ${t.version ? `v${t.version}` : ''}
      </button>
    `).join('');
  } catch (err) {
    console.error('Failed to load software templates', err);
  }
}

async function loadSoftwareHistory() {
  try {
    const response = await fetch('/api/software/history');
    const history = await response.json();
    const container = document.getElementById('software-history-list');
    if (!container) return;

    if (history.length === 0) {
      container.innerHTML = '<div style="text-align:center; color:#8b949e;">No history yet</div>';
      return;
    }

    container.innerHTML = history.slice(0, 8).map(h => `
      <div style="padding:6px; background:rgba(255,255,255,0.04); border-radius:6px; color:#cbd5e1;">
        <div style="font-weight:600; font-size:0.85rem;">${h.package_name} ${h.package_version ? `v${h.package_version}` : ''}</div>
        <div style="font-size:0.75rem; color:#8b949e;">
          <span style="color:${h.status === 'success' ? '#22c55e' : h.status === 'failed' ? '#ef4444' : '#f59e0b'}">${h.status.toUpperCase()}</span>
          · ${new Date(h.created_at).toLocaleString()}
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load software history', err);
  }
}

async function installPackage(packageName, packageVersion = null) {
  const selectedServers = Array.from(document.querySelectorAll('.server-select:checked')).map(cb => parseInt(cb.value));
  
  if (selectedServers.length === 0) {
    alert('Please select at least one server');
    return;
  }

  if (!packageName.trim()) {
    alert('Please enter a package name');
    return;
  }

  try {
    const response = await fetch('/api/software/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        server_ids: selectedServers,
        package_name: packageName.trim(),
        package_version: packageVersion ? packageVersion.trim() : null
      })
    });

    const data = await response.json();
    if (response.ok) {
      alert(`Installation started for ${packageName}`);
      document.getElementById('software-package-input').value = '';
      document.getElementById('software-version-input').value = '';
      setTimeout(() => {
        loadSoftwareHistory();
      }, 1000);
    } else {
      alert(`Error: ${data.error}`);
    }
  } catch (err) {
    console.error('Failed to install package', err);
    alert('Failed to install package');
  }
}

function quickInstallTemplate(packageName, templateName) {
  const selectedServers = Array.from(document.querySelectorAll('.server-select:checked')).map(cb => parseInt(cb.value));
  
  if (selectedServers.length === 0) {
    alert('Please select at least one server');
    return;
  }

  if (confirm(`Install ${templateName}?`)) {
    installPackage(packageName, null);
  }
}

document.addEventListener('DOMContentLoaded', function() {
  const installBtn = document.getElementById('install-package-btn');
  if (installBtn) {
    installBtn.addEventListener('click', function() {
      const packageName = document.getElementById('software-package-input').value;
      const packageVersion = document.getElementById('software-version-input').value;
      installPackage(packageName, packageVersion);
    });
  }

  const refreshBtn = document.getElementById('refresh-software-templates');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadSoftwareTemplates);
  }

  loadSoftwareTemplates();
  loadSoftwareHistory();

  setInterval(loadSoftwareHistory, 10000);
});
