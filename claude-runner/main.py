#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import subprocess
import requests
import sys
from typing import Dict, Any
from datetime import datetime, timezone

# Configure logging with immediate flush for container visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)


class ClaudeRunner:
    def __init__(self):
        self.session_name = os.getenv("RESEARCH_SESSION_NAME", "")
        self.session_namespace = os.getenv("RESEARCH_SESSION_NAMESPACE", "default")
        self.prompt = os.getenv("PROMPT", "")
        self.website_url = os.getenv("WEBSITE_URL", "")
        self.timeout = int(os.getenv("TIMEOUT", "300"))
        self.backend_api_url = os.getenv(
            "BACKEND_API_URL", "http://backend-service:8080/api"
        )

        # Validate Anthropic API key for Claude Code
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        logger.info(f"Initialized ClaudeRunner for session: {self.session_name}")
        logger.info(f"Website URL: {self.website_url}")
        logger.info("Using Claude Code CLI with Playwright MCP")

    async def run_research_session(self):
        """Main method to run the research session"""
        try:
            logger.info(
                "Starting research session with Claude Code + Playwright MCP..."
            )

            # Update status to indicate we're starting
            await self.update_session_status(
                {
                    "phase": "Running",
                    "message": "Initializing Claude Code with Playwright MCP browser capabilities",
                    "startTime": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Create comprehensive research prompt for Claude Code with MCP tools
            research_prompt = self._create_research_prompt()

            # Update status
            await self.update_session_status(
                {
                    "phase": "Running",
                    "message": f"Claude Code analyzing {self.website_url} with agentic browser automation",
                }
            )

            # Run Claude Code with our research prompt
            logger.info("Running Claude Code with MCP browser automation...")

            result = await self._run_claude_code(research_prompt)

            logger.info("Received comprehensive research analysis from Claude Code")

            # Update the session with the final result
            await self.update_session_status(
                {
                    "phase": "Completed",
                    "message": "Research completed successfully using Claude Code + Playwright MCP",
                    "completionTime": datetime.now(timezone.utc).isoformat(),
                    "finalOutput": result,
                }
            )

            logger.info("Research session completed successfully")

        except Exception as e:
            logger.error(f"Research session failed: {str(e)}")

            # Update status to indicate failure
            await self.update_session_status(
                {
                    "phase": "Failed",
                    "message": f"Research failed: {str(e)}",
                    "completionTime": datetime.now(timezone.utc).isoformat(),
                }
            )

            sys.exit(1)

    async def _run_claude_code(self, prompt: str) -> str:
        """Run Claude Code CLI with the research prompt"""
        try:
            # Set up environment with API key
            env = os.environ.copy()
            env["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")

            # Debug: Check working directory and files
            logger.info(f"Working directory: {os.getcwd()}")
            logger.info(
                f"Files in /app: {os.listdir('/app') if os.path.exists('/app') else 'Directory not found'}"
            )

            # Check if Claude Code CLI is available
            try:
                which_result = subprocess.run(
                    ["which", "claude"], capture_output=True, text=True
                )
                logger.info(
                    f"Claude CLI location: {which_result.stdout.strip() if which_result.returncode == 0 else 'not found'}"
                )
            except Exception as e:
                logger.warning(f"Could not check Claude CLI location: {e}")

            # Check Claude Code CLI version
            try:
                version_result = subprocess.run(
                    ["claude", "--version"], capture_output=True, text=True, timeout=10
                )
                logger.info(
                    f"Claude CLI version: {version_result.stdout.strip() if version_result.returncode == 0 else 'version check failed'}"
                )
                if version_result.stderr:
                    logger.info(
                        f"Claude CLI version stderr: {version_result.stderr.strip()}"
                    )
            except Exception as e:
                logger.warning(f"Could not check Claude CLI version: {e}")

            # Use correct Claude CLI syntax with --print for non-interactive output
            # Add flags for container/automated execution
            command = [
                "claude",
                "--print",
                "--output-format",
                "text",
                "--dangerously-skip-permissions",  # Skip permission dialogs in container
                "--mcp-config",
                "/app/.mcp.json",  # Explicit MCP config
                prompt,
            ]
            logger.info(
                f"Attempting command: claude --print --output-format text --dangerously-skip-permissions --mcp-config /app/.mcp.json '<PROMPT>'"
            )
            logger.info(f"Prompt length: {len(prompt)} characters")
            logger.info(
                f"API key present: {'Yes' if env.get('ANTHROPIC_API_KEY') else 'No'}"
            )

            # For non-interactive mode with MCP servers
            logger.info("Creating subprocess...")

            # Create process with prompt passed as argument (no stdin needed)
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd="/app",  # This directory must contain .claude file
            )

            logger.info(f"Process created with PID: {process.pid}")
            logger.info(
                "Using --print mode, prompt passed as argument - no stdin interaction needed"
            )

            # Add progress logging during execution
            logger.info(
                f"Waiting for process to complete (timeout: {self.timeout}s)..."
            )
            start_time = asyncio.get_event_loop().time()

            async def log_progress():
                """Log progress periodically with process status"""
                while process.returncode is None:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.info(
                        f"Claude Code process still running... elapsed: {elapsed:.1f}s (PID: {process.pid})"
                    )
                    # Note: Manual flush may be redundant due to PYTHONUNBUFFERED=1
                    await asyncio.sleep(
                        15
                    )  # Log every 15 seconds for better visibility

            # Start progress logging task
            progress_task = asyncio.create_task(log_progress())

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
                progress_task.cancel()

                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"Process completed in {elapsed:.1f}s")

            except asyncio.TimeoutError:
                progress_task.cancel()
                logger.error(f"Process timed out after {self.timeout} seconds")

                # Try to get partial output before killing
                try:
                    process.kill()
                    await process.wait()
                except Exception as kill_error:
                    logger.error(f"Error killing process: {kill_error}")

                raise RuntimeError(
                    f"Claude Code execution timed out after {self.timeout} seconds"
                )

            # Log process results
            logger.info(f"Process return code: {process.returncode}")

            if stderr:
                stderr_text = stderr.decode().strip()
                if stderr_text:
                    logger.info(f"Process stderr: {stderr_text}")

            if stdout:
                stdout_text = stdout.decode().strip()
                logger.info(f"Process stdout length: {len(stdout_text)} characters")
                if len(stdout_text) > 0:
                    logger.info(
                        f"Process stdout preview: {stdout_text[:200]}{'...' if len(stdout_text) > 200 else ''}"
                    )

            if process.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                logger.error(
                    f"Claude Code process failed with return code {process.returncode}"
                )
                logger.error(f"Error details: {error_msg}")
                raise RuntimeError(
                    f"Claude Code failed with return code {process.returncode}: {error_msg}"
                )

            result = stdout.decode().strip() if stdout else ""

            if not result:
                logger.warning("Claude Code returned empty result")
                raise RuntimeError("Claude Code returned empty result")

            logger.info(
                f"Claude Code completed successfully, output length: {len(result)} characters"
            )
            return result

        except Exception as e:
            logger.error(f"Error running Claude Code: {str(e)}")
            # Note: PYTHONUNBUFFERED=1 should handle this automatically
            raise
        finally:
            # Note: PYTHONUNBUFFERED=1 should auto-flush
            pass

    def _create_research_prompt(self) -> str:
        """Create a comprehensive research prompt for Claude Code with MCP browser instructions"""
        return f"""You are a research assistant with browser automation capabilities via Playwright MCP tools. 

RESEARCH OBJECTIVE: {self.prompt}

TARGET WEBSITE: {self.website_url}

INSTRUCTIONS:
Please use your Playwright MCP browser tools to thoroughly research and analyze the website: {self.website_url}

BROWSER AUTOMATION TASKS:
1. Navigate to the website and take a snapshot to see what's there
2. Extract and analyze all text content from the page
3. Take a screenshot for visual reference
4. Identify key navigation elements, links, and page structure
5. Look for forms, interactive elements, or important functionality
6. Extract metadata (title, description, etc.)
7. If needed, interact with the page to access additional content or sections

RESEARCH ANALYSIS REQUIREMENTS:
Based on your browser-based investigation, provide a comprehensive report with:

1. **Website Overview**
   - Website purpose and main functionality
   - Target audience and primary use case
   - Overall design and user experience assessment

2. **Content Analysis** 
   - Key information and main content themes
   - Important sections and navigation structure
   - Notable features or unique functionality

3. **Research Objective Analysis**
   - How well does this website address: "{self.prompt}"
   - Specific findings directly relevant to the research question
   - Key insights and actionable takeaways

4. **Technical & UX Observations**
   - Page performance and loading characteristics
   - Visual design and layout assessment
   - Any technical issues or accessibility concerns
   - Mobile responsiveness if observable

5. **Recommendations & Strategic Insights**
   - Actionable recommendations based on findings
   - Suggested follow-up research areas or questions
   - Competitive analysis insights if applicable
   - Overall assessment and conclusion

IMPORTANT: Use your MCP browser tools extensively and agentically. Take screenshots, navigate through sections, and extract comprehensive information before providing your analysis. Be thorough and methodical in your approach.

Remember: You have full browser automation capabilities through MCP - use them to their fullest extent to gather comprehensive data!"""

    async def update_session_status(self, status_update: Dict[str, Any]):
        """Update the ResearchSession status via the backend API"""
        try:
            url = f"{self.backend_api_url}/research-sessions/{self.session_name}/status"

            logger.info(
                f"Updating session status: {status_update.get('phase', 'unknown')}"
            )

            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: requests.put(url, json=status_update, timeout=30)
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to update session status: {response.status_code} - {response.text}"
                )
            else:
                logger.info("Session status updated successfully")
                # Note: Status updates are critical - keep one flush here
                sys.stdout.flush()

        except Exception as e:
            logger.error(f"Error updating session status: {str(e)}")
            # Don't raise here as this shouldn't stop the main process


async def main():
    """Main entry point"""
    logger.info("Claude Research Runner with Claude Code + Playwright MCP starting...")

    # Validate required environment variables
    required_vars = [
        "RESEARCH_SESSION_NAME",
        "PROMPT",
        "WEBSITE_URL",
        "ANTHROPIC_API_KEY",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        sys.exit(1)

    try:
        runner = ClaudeRunner()
        await runner.run_research_session()

    except KeyboardInterrupt:
        logger.info("Research session interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
