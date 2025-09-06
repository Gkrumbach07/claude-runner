#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import sys
import subprocess
import requests
from typing import Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
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
                    "startTime": datetime.now().isoformat(),
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
                    "completionTime": datetime.now().isoformat(),
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
                    "completionTime": datetime.now().isoformat(),
                }
            )

            sys.exit(1)

    async def _run_claude_code(self, prompt: str) -> str:
        """Run Claude Code CLI with the research prompt"""
        try:
            # Set up environment with API key
            env = os.environ.copy()
            env["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")

            # Run Claude Code CLI
            logger.info("Executing Claude Code CLI...")

            # For interactive mode with MCP servers
            process = await asyncio.create_subprocess_exec(
                "claude",
                "--prompt",
                prompt,  # Pass prompt directly instead of file
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                env=env,
                cwd="/app",  # This directory must contain .claude file
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise RuntimeError(
                    f"Claude Code execution timed out after {self.timeout} seconds"
                )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(
                    f"Claude Code failed with return code {process.returncode}: {error_msg}"
                )

            result = stdout.decode().strip()

            if not result:
                raise RuntimeError("Claude Code returned empty result")

            logger.info(
                f"Claude Code completed successfully, output length: {len(result)}"
            )
            return result

        except Exception as e:
            logger.error(f"Error running Claude Code: {str(e)}")
            raise
        finally:
            # No cleanup needed for interactive mode
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
