import argparse
import json
import requests
from agents.config import BACKEND_URL, REPORT_ENDPOINT
from agents.system_info import metrics_payload


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


if __name__ == "__main__":
    main()
