"""
Package manager module for handling software installation via Chocolatey on Windows.
"""
import subprocess
import shutil
import os
from backend.ansible_manager import run_command


def chocolatey_installed(servers):
    """
    Check if Chocolatey is installed on target servers.
    
    Args:
        servers: List of server objects or dicts
        
    Returns:
        dict with returncode, stdout, stderr, and list of servers with Chocolatey
    """
    if not servers:
        return {"returncode": 1, "error": "No servers provided"}
    
    result = run_command(servers, 'choco --version')
    return result


def install_package(servers, package_name, package_version=None):
    """
    Install a package via Chocolatey on target servers.
    
    Args:
        servers: List of server objects or dicts
        package_name: Name of the package to install (e.g., '7zip', 'git', 'nodejs')
        package_version: Optional version string (e.g., '18.0.0')
        
    Returns:
        dict with returncode, stdout, stderr
    """
    if not servers:
        return {"returncode": 1, "stdout": "", "stderr": "No servers provided", "error": "No servers provided"}
    
    if not package_name or not isinstance(package_name, str):
        return {"returncode": 1, "stdout": "", "stderr": "Invalid package name", "error": "Invalid package name"}
    
    version_flag = f"--version={package_version}" if package_version else ""
    cmd = f"choco install {package_name} -y --no-progress {version_flag}".strip()
    
    result = run_command(servers, cmd)
    return result


def uninstall_package(servers, package_name):
    """
    Uninstall a package via Chocolatey on target servers.
    
    Args:
        servers: List of server objects or dicts
        package_name: Name of the package to uninstall
        
    Returns:
        dict with returncode, stdout, stderr
    """
    if not servers:
        return {"returncode": 1, "stdout": "", "stderr": "No servers provided", "error": "No servers provided"}
    
    if not package_name or not isinstance(package_name, str):
        return {"returncode": 1, "stdout": "", "stderr": "Invalid package name", "error": "Invalid package name"}
    
    cmd = f"choco uninstall {package_name} -y --no-progress"
    
    result = run_command(servers, cmd)
    return result


def list_installed_packages(servers):
    """
    List installed packages on target servers.
    
    Args:
        servers: List of server objects or dicts
        
    Returns:
        dict with returncode, stdout, stderr containing list of packages
    """
    if not servers:
        return {"returncode": 1, "stdout": "", "stderr": "No servers provided", "error": "No servers provided"}
    
    result = run_command(servers, "choco list --local-only")
    return result


def upgrade_package(servers, package_name):
    """
    Upgrade a package via Chocolatey on target servers.
    
    Args:
        servers: List of server objects or dicts
        package_name: Name of the package to upgrade
        
    Returns:
        dict with returncode, stdout, stderr
    """
    if not servers:
        return {"returncode": 1, "stdout": "", "stderr": "No servers provided", "error": "No servers provided"}
    
    if not package_name or not isinstance(package_name, str):
        return {"returncode": 1, "stdout": "", "stderr": "Invalid package name", "error": "Invalid package name"}
    
    cmd = f"choco upgrade {package_name} -y --no-progress"
    
    result = run_command(servers, cmd)
    return result
