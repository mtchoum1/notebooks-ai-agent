#!/usr/bin/env python3
"""DevAssist Daemon Worker - Runs periodic briefs and stores them.

This script is designed to run in a container/pod on OpenShift.
It generates morning briefs at configurable intervals and stores them in a database.
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from devassist.db.models import Brief
from devassist.db.storage import get_storage
from devassist.mcp.client import MCPClient
from devassist.mcp.registry import MCPRegistry
from devassist.orchestrator.agent import OrchestrationAgent
from devassist.orchestrator.llm_client import AnthropicLLMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Configuration from environment
INTERVAL_MINUTES = int(os.environ.get("DEVASSIST_INTERVAL_MINUTES", "60"))
USER_ID = os.environ.get("DEVASSIST_USER_ID", "default")
SOURCES = os.environ.get("DEVASSIST_SOURCES", "jira,github").split(",")

# Graceful shutdown
shutdown_event = asyncio.Event()


def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def generate_brief() -> Brief | None:
    """Generate a morning brief using the orchestration agent."""
    logger.info(f"Generating brief for user {USER_ID} with sources: {SOURCES}")
    
    try:
        # Initialize components
        llm_client = AnthropicLLMClient()
        mcp_client = MCPClient()
        registry = MCPRegistry()
        
        # Build list of server configs to connect
        server_configs = []
        for source in SOURCES:
            source = source.strip()
            config = registry.get(source)
            if config and config.is_configured():
                server_configs.append(config)
            else:
                logger.warning(f"Source '{source}' not configured, skipping")
        
        if not server_configs:
            logger.error("No configured sources available")
            return None
        
        # Connect to MCP servers and generate brief
        async with mcp_client.connect_many(server_configs):
            agent = OrchestrationAgent(
                llm_client=llm_client,
                mcp_client=mcp_client,
                registry=registry,
            )
            
            prompt = "Give me a morning brief with all important updates, issues, and action items."
            response = await agent.process(prompt)
            
            # Create Brief object
            brief = Brief(
                user_id=USER_ID,
                created_at=datetime.utcnow(),
                summary=response.content[:500] if response.content else "",
                sources_used=response.sources_used,
                raw_response=response.content,
            )
            
            return brief
            
    except Exception as e:
        logger.exception(f"Error generating brief: {e}")
        return None


async def run_daemon():
    """Main daemon loop."""
    logger.info("=" * 60)
    logger.info("DevAssist Daemon Worker Starting")
    logger.info(f"  User ID: {USER_ID}")
    logger.info(f"  Sources: {SOURCES}")
    logger.info(f"  Interval: {INTERVAL_MINUTES} minutes")
    logger.info("=" * 60)
    
    storage = get_storage()
    logger.info(f"Using storage backend: {type(storage).__name__}")
    
    while not shutdown_event.is_set():
        try:
            # Generate brief
            brief = await generate_brief()
            
            if brief:
                # Save to database
                brief_id = storage.save_brief(brief)
                logger.info(f"✓ Brief saved with ID: {brief_id}")
                logger.info(f"  Sources used: {brief.sources_used}")
                logger.info(f"  Summary length: {len(brief.raw_response)} chars")
            else:
                logger.warning("Failed to generate brief")
            
        except Exception as e:
            logger.exception(f"Error in daemon loop: {e}")
        
        # Wait for next interval or shutdown
        logger.info(f"Sleeping for {INTERVAL_MINUTES} minutes...")
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=INTERVAL_MINUTES * 60
            )
            # If we get here, shutdown was requested
            break
        except asyncio.TimeoutError:
            # Normal timeout, continue loop
            pass
    
    logger.info("Daemon shutdown complete")


def main():
    """Entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Run the daemon
    asyncio.run(run_daemon())


if __name__ == "__main__":
    main()
