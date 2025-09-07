#!/usr/bin/env python3

import os
import subprocess
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_claude_binary():
    """Test Claude binary in various ways to identify the hanging issue"""

    logger.info("=== CLAUDE CLI DEBUGGING ===")

    # Test 1: Check if claude binary exists and is executable
    logger.info("1. Testing claude binary existence...")
    try:
        result = subprocess.run(
            ["which", "claude"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            claude_path = result.stdout.strip()
            logger.info(f"✅ Claude binary found at: {claude_path}")

            # Check permissions
            try:
                import stat

                st = os.stat(claude_path)
                logger.info(f"Claude binary permissions: {oct(st.st_mode)}")
                logger.info(
                    f"Claude binary is executable: {bool(st.st_mode & stat.S_IXUSR)}"
                )
            except Exception as e:
                logger.error(f"Error checking claude permissions: {e}")
        else:
            logger.error("❌ Claude binary not found in PATH")
            return
    except Exception as e:
        logger.error(f"Error finding claude binary: {e}")
        return

    # Test 2: Check Node.js (Claude CLI is Node-based)
    logger.info("2. Testing Node.js environment...")
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info(f"✅ Node.js version: {result.stdout.strip()}")
        else:
            logger.error("❌ Node.js not working")
    except Exception as e:
        logger.error(f"Node.js test failed: {e}")

    # Test 3: Check npm environment
    logger.info("3. Testing npm environment...")
    try:
        result = subprocess.run(
            ["npm", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info(f"✅ npm version: {result.stdout.strip()}")
        else:
            logger.error("❌ npm not working")
    except Exception as e:
        logger.error(f"npm test failed: {e}")

    # Test 4: Check environment variables that might affect Claude
    logger.info("4. Checking environment variables...")
    env_vars = ["HOME", "USER", "PATH", "NODE_ENV", "ANTHROPIC_API_KEY"]
    for var in env_vars:
        value = os.getenv(var, "NOT_SET")
        if var == "ANTHROPIC_API_KEY" and value != "NOT_SET":
            logger.info(f"{var}: [REDACTED - length {len(value)}]")
        else:
            logger.info(f"{var}: {value}")

    # Test 5: Try claude --version with very short timeout
    logger.info("5. Testing 'claude --version' with 10s timeout...")
    try:
        start_time = time.time()
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=10
        )
        elapsed = time.time() - start_time
        logger.info(f"✅ Claude --version completed in {elapsed:.2f}s")
        logger.info(f"Return code: {result.returncode}")
        logger.info(f"Stdout: {result.stdout}")
        logger.info(f"Stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("❌ Claude --version HUNG after 10 seconds")
        logger.error(
            "This indicates a fundamental issue with the Claude CLI in this environment"
        )
    except Exception as e:
        logger.error(f"Claude --version failed: {e}")

    # Test 6: Try to trace what claude is doing (if possible)
    logger.info("6. Testing claude with strace (if available)...")
    try:
        # Check if strace is available
        subprocess.run(["which", "strace"], capture_output=True, text=True, timeout=2)
        logger.info("Trying strace on claude --version...")
        result = subprocess.run(
            [
                "timeout",
                "10",
                "strace",
                "-f",
                "-e",
                "trace=network,file",
                "claude",
                "--version",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        logger.info(f"Strace output (stderr): {result.stderr[:1000]}")
    except Exception as e:
        logger.info(f"Strace not available or failed: {e}")

    logger.info("=== DEBUGGING COMPLETE ===")


if __name__ == "__main__":
    logger.info("Starting Claude CLI debugging...")
    test_claude_binary()
