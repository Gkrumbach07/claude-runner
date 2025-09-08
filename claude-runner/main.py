#!/usr/bin/env python3

import asyncio
import logging
import os
import requests
import sys
from typing import Dict, Any
from datetime import datetime, timezone

# Import Claude Code Python SDK
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

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
        """Run Claude Code using Python SDK with MCP browser automation"""
        try:
            logger.info("Initializing Claude Code Python SDK with MCP server...")

            # Configure SDK with MCP server and browser tools
            options = ClaudeCodeOptions(
                system_prompt="You are a research assistant with browser automation capabilities via Playwright MCP tools.",
                max_turns=5,
                permission_mode="acceptEdits",
                allowed_tools=["mcp__playwright"],
                mcp_servers="/app/.mcp.json",
                cwd="/app",
            )

            logger.info("Creating Claude SDK client with MCP browser automation...")

            async with ClaudeSDKClient(options=options) as client:
                logger.info("SDK Client initialized successfully with MCP tools")

                # Send the research prompt
                logger.info("Sending research query to Claude Code SDK...")
                await client.query(prompt)

                # Collect streaming response
                response_text = []
                cost = 0.0
                duration = 0

                logger.info("Processing streaming response from Claude...")
                async for message in client.receive_response():
                    # Stream content as it arrives
                    if hasattr(message, "content"):
                        for block in message.content:
                            if hasattr(block, "text"):
                                text = block.text
                                response_text.append(text)
                                # Stream model output to logs in real-time
                                if text.strip():  # Only log non-empty text
                                    logger.info(f"[MODEL OUTPUT] {text}")

                    # Get final result with metadata
                    if type(message).__name__ == "ResultMessage":
                        cost = getattr(message, "total_cost_usd", 0.0)
                        duration = getattr(message, "duration_ms", 0)

                # Combine response
                result = "".join(response_text)

                if not result.strip():
                    raise RuntimeError("Claude Code SDK returned empty result")

                logger.info(f"Research completed successfully ({len(result)} chars)")
                logger.info(f"Cost: ${cost:.4f}, Duration: {duration}ms")

                return result

        except Exception as e:
            logger.error(f"Error running Claude Code SDK: {str(e)}")
            raise

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
