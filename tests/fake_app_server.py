from __future__ import annotations

import argparse
import json
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="normal")
    parser.add_argument("--codex-home", default=r"C:\DraftRoot\codex-home")
    # Accept trailing positional args like 'app-server' '--stdio'
    parser.add_argument("extra", nargs="*")
    args = parser.parse_args()

    mode = args.mode
    codex_home = args.codex_home

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line_str = line.strip()
        if not line_str:
            continue

        try:
            req = json.loads(line_str)
        except json.JSONDecodeError:
            continue

        if not isinstance(req, dict):
            continue

        req_id = req.get("id")
        method = req.get("method")

        # Handle notifications (no id)
        if req_id is None:
            continue

        if mode == "crash":
            sys.stderr.write("Simulated server crash\n")
            sys.exit(2)

        if mode == "hang":
            time.sleep(60)

        if mode == "noisy_stderr":
            for i in range(50000):
                sys.stderr.write(f"Simulated noisy stderr line {i}\n")
            sys.stderr.flush()

        if mode == "rpc_error":
            response = {
                "id": req_id,
                "error": {"code": -32600, "message": "Simulated RPC error"},
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        if method == "initialize":
            res = {
                "userAgent": "codex-test/1.0.0",
                "codexHome": codex_home,
                "platformFamily": "windows",
                "platformOs": "windows",
            }
            sys.stdout.write(json.dumps({"id": req_id, "result": res}) + "\n")
            sys.stdout.flush()

        elif method == "account/read":
            res = {
                "requiresOpenaiAuth": True,
                "account": {
                    "type": "chatgpt",
                    "email": "guard.test@example.com",
                    "planType": "plus",
                },
            }
            sys.stdout.write(json.dumps({"id": req_id, "result": res}) + "\n")
            sys.stdout.flush()

        elif method == "account/rateLimits/read":
            if mode == "null_credits":
                res = {
                    "rateLimits": {},
                    "rateLimitsByLimitId": None,
                    "rateLimitResetCredits": None,
                }
            elif mode == "null_credits_list":
                res = {
                    "rateLimits": {},
                    "rateLimitsByLimitId": None,
                    "rateLimitResetCredits": {
                        "availableCount": 2,
                        "credits": None,
                    },
                }
            elif mode == "unlisted_credits":
                res = {
                    "rateLimits": {},
                    "rateLimitsByLimitId": None,
                    "rateLimitResetCredits": {
                        "availableCount": 3,
                        "credits": [
                            {
                                "id": "credit_1",
                                "expiresAt": 1754136000,
                                "grantedAt": 1753531200,
                                "resetType": "weekly",
                                "status": "available",
                                "title": "Weekly Reset Credit",
                                "description": "Available reset credit",
                            }
                        ],
                    },
                }
            elif mode == "timestamp_string_and_iso":
                res = {
                    "rateLimits": {},
                    "rateLimitsByLimitId": None,
                    "rateLimitResetCredits": {
                        "availableCount": 2,
                        "credits": [
                            {
                                "id": "credit_str_int",
                                "expires_at": "1754136000",
                                "granted_at": "1753531200",
                                "resetType": "weekly",
                                "status": "available",
                                "title": "String Int Credit",
                                "description": "Credit with string integer timestamp",
                            },
                            {
                                "id": "credit_iso",
                                "expiresAt": "2026-08-02T12:00:00Z",
                                "grantedAt": "2026-07-26T12:00:00Z",
                                "resetType": "monthly",
                                "status": "available",
                                "title": "ISO Credit",
                                "description": "Credit with ISO timestamp",
                            },
                        ],
                    },
                }
            else:
                # normal
                res = {
                    "rateLimits": {
                        "limitId": "codex",
                        "planType": "plus",
                        "primary": {
                            "usedPercent": 25.0,
                            "windowDurationMins": 10080,
                            "resetsAt": 1754136000,
                        },
                        "secondary": {
                            "usedPercent": 15.0,
                            "windowDurationMins": 300,
                            "resetsAt": 1753550000,
                        },
                        "credits": {
                            "hasCredits": True,
                            "unlimited": False,
                            "balance": None,
                        },
                        "spendControlReached": False,
                        "rateLimitReachedType": None,
                    },
                    "rateLimitsByLimitId": None,
                    "rateLimitResetCredits": {
                        "availableCount": 1,
                        "credits": [
                            {
                                "id": "credit_default",
                                "expiresAt": 1754136000,
                                "grantedAt": 1753531200,
                                "resetType": "weekly",
                                "status": "available",
                                "title": "Weekly Reset Credit",
                                "description": "Available reset credit",
                            }
                        ],
                    },
                }
            sys.stdout.write(json.dumps({"id": req_id, "result": res}) + "\n")
            sys.stdout.flush()

        else:
            response = {
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
