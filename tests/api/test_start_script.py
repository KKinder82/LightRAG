"""Verify the deployment launcher includes its server/provider dependencies."""

import os
from pathlib import Path
import subprocess


def test_start_script_requests_api_and_provider_extras(tmp_path):
    script = Path(__file__).resolve().parents[2] / "start_01.sh"
    fake_uv = tmp_path / "uv"
    fake_uv.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@"\n')
    fake_uv.chmod(0o755)
    result = subprocess.run(
        ["bash", str(script)],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.splitlines()
    assert output[0] == str(script.parent)
    assert output[1:] == [
        "run", "--extra", "api", "--extra", "offline-llm",
        "lightrag-server", "--port", "9621", "--workspace", "space1",
    ]


def test_start_script_does_not_pass_desktop_proxies_to_server(tmp_path):
    script = Path(__file__).resolve().parents[2] / "start_01.sh"
    fake_uv = tmp_path / "uv"
    fake_uv.write_text('#!/bin/sh\n/usr/bin/env\n')
    fake_uv.chmod(0o755)
    proxy_names = ["ALL_PROXY", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        **{key: "socks://invalid-test-proxy:7890" for key in proxy_names},
        "LIGHTRAG_LAUNCH_TEST": "preserved",
    }
    result = subprocess.run(
        ["bash", str(script)], cwd=tmp_path, env=environment,
        check=True, capture_output=True, text=True,
    )
    passed = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    assert not any(key in passed for key in proxy_names)
    assert passed["LIGHTRAG_LAUNCH_TEST"] == "preserved"
    assert environment["ALL_PROXY"] == "socks://invalid-test-proxy:7890"
