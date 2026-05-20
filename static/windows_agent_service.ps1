<#
Sample Windows service installer for the AlfaMonitor agent.
Run this script as Administrator after copying the agent files to the target host.
#>

$serviceName = "AlfaMonitorAgent"
$pythonExe = "C:\Python39\python.exe"
$agentPath = "C:\AlfaMonitorAgent\agent.py"
$backendUrl = "http://localhost:5000"
$agentUser = "agent"
$agentPort = "3389"

if (!(Test-Path $pythonExe)) {
    Write-Error "Python executable not found at $pythonExe"
    exit 1
}

if (!(Test-Path $agentPath)) {
    Write-Error "Agent script not found at $agentPath"
    exit 1
}

$binPath = "`"$pythonExe`" `"$agentPath`" --host $backendUrl --username $agentUser --port $agentPort"

Write-Output "Creating Windows service '$serviceName'..."
sc.exe create $serviceName binPath= $binPath start= auto obj= LocalSystem DisplayName= "AlfaMonitor Agent"
sc.exe description $serviceName "AlfaMonitor Windows agent service. Runs with highest privileges for dashboard software installation."

Write-Output "Starting service '$serviceName'..."
sc.exe start $serviceName

Write-Output "Service $serviceName created and started."
Write-Output "If you need to change paths, edit this script before running it."
