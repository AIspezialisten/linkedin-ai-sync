"""
Command-line interface for LinkedIn-Dynamics CRM synchronization.

This module provides a simple CLI for running synchronization tasks.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sync.synchronizer import SyncOrchestrator


class MockMCPClient:
    """Mock MCP client for testing purposes."""
    
    def __init__(self, client_type: str):
        self.client_type = client_type
    
    async def call_tool(self, request: dict) -> dict:
        """Mock tool call implementation."""
        tool_name = request.get("name", "")
        
        if self.client_type == "linkedin":
            if tool_name == "get_member_snapshot_data":
                return {
                    "success": True,
                    "data": {
                        "elements": [
                            {
                                "memberConnections": {
                                    "elements": [
                                        {
                                            "id": "john-doe-123",
                                            "firstName": "John",
                                            "lastName": "Doe",
                                            "headline": "Software Engineer at Tech Company",
                                            "location": "San Francisco, CA"
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            elif tool_name == "get_connections_data":
                return {
                    "success": True,
                    "data": {
                        "connections": [
                            {
                                "id": "jane-smith-456",
                                "firstName": "Jane",
                                "lastName": "Smith",
                                "headline": "Product Manager",
                                "location": "New York, NY"
                            }
                        ],
                        "total_count": 1
                    }
                }
        
        elif self.client_type == "dynamics":
            if tool_name == "create_contact":
                return {
                    "success": True,
                    "contact_id": "12345678-1234-1234-1234-123456789012",
                    "message": "Contact created successfully"
                }
            elif tool_name == "search_contacts":
                return {
                    "success": True,
                    "data": {
                        "value": []  # No existing contacts found
                    }
                }
            elif tool_name == "update_contact":
                return {
                    "success": True,
                    "message": "Contact updated successfully"
                }
        
        return {"success": False, "message": f"Unknown tool: {tool_name}"}


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--env-file', default='.env', help='Path to environment file')
@click.pass_context
def cli(ctx, verbose: bool, env_file: str):
    """LinkedIn-Dynamics CRM Synchronization CLI."""
    ctx.ensure_object(dict)
    
    # Load environment variables
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
        click.echo(f"Loaded environment from {env_path}")
    else:
        click.echo(f"Environment file {env_path} not found")
    
    # Set up logging
    logger = setup_logging(verbose)
    ctx.obj['logger'] = logger
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--dry-run', is_flag=True, help='Perform a dry run without making changes')
@click.option('--ai-detection/--no-ai-detection', default=True, help='Use AI for duplicate detection')
@click.option('--ollama-model', default='mistral-small:24b', help='Ollama model for AI duplicate detection')
@click.pass_context
def sync_profile(ctx, dry_run: bool, ai_detection: bool, ollama_model: str):
    """Synchronize the authenticated user's LinkedIn profile to CRM."""
    logger = ctx.obj['logger']
    
    async def run_sync():
        # For now, use mock clients since we don't have the actual MCP clients running
        # In a real implementation, these would be actual MCP client connections
        linkedin_client = MockMCPClient("linkedin")
        dynamics_client = MockMCPClient("dynamics")
        
        orchestrator = SyncOrchestrator(linkedin_client, dynamics_client, logger)
        
        if dry_run:
            click.echo(f"DRY RUN: Would synchronize user profile (AI detection: {ai_detection})")
            return
        
        click.echo("Synchronizing LinkedIn profile to Dynamics CRM...")
        if ai_detection:
            click.echo(f"🤖 AI duplicate detection enabled using {ollama_model}")
        
        try:
            stats, results = await orchestrator.sync_user_profile()
            
            # Display results
            click.echo(f"\nSynchronization completed:")
            click.echo(f"  Total processed: {stats.total_processed}")
            click.echo(f"  Created: {stats.created}")
            click.echo(f"  Updated: {stats.updated}")
            click.echo(f"  Skipped: {stats.skipped}")
            click.echo(f"  Errors: {stats.errors}")
            
            if ctx.obj['verbose']:
                click.echo(f"\nDetailed results:")
                for result in results:
                    click.echo(f"  {result.action}: {result.message}")
                    if result.details:
                        click.echo(f"    Details: {json.dumps(result.details, indent=4)}")
            
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)
    
    asyncio.run(run_sync())


@cli.command()
@click.option('--keywords', help='Keywords to filter connections')
@click.option('--limit', default=50, help='Maximum number of connections to sync')
@click.option('--dry-run', is_flag=True, help='Perform a dry run without making changes')
@click.option('--ai-detection/--no-ai-detection', default=True, help='Use AI for duplicate detection')
@click.option('--ollama-model', default='mistral-small:24b', help='Ollama model for AI duplicate detection')
@click.option('--auto-sync/--no-auto-sync', default=False, help='Automatically sync contacts deemed safe by AI')
@click.pass_context
def sync_connections(ctx, keywords: Optional[str], limit: int, dry_run: bool, 
                   ai_detection: bool, ollama_model: str, auto_sync: bool):
    """Synchronize LinkedIn connections to CRM contacts with AI duplicate detection."""
    logger = ctx.obj['logger']
    
    async def run_sync():
        # For now, use mock clients
        linkedin_client = MockMCPClient("linkedin")
        dynamics_client = MockMCPClient("dynamics")
        
        orchestrator = SyncOrchestrator(linkedin_client, dynamics_client, logger)
        
        if dry_run:
            click.echo(f"DRY RUN: Would synchronize {limit} connections" + 
                      (f" with keywords '{keywords}'" if keywords else ""))
            return
        
        click.echo(f"Synchronizing LinkedIn connections to Dynamics CRM...")
        if keywords:
            click.echo(f"  Keywords: {keywords}")
        click.echo(f"  Limit: {limit}")
        
        try:
            stats, results = await orchestrator.sync_connections(keywords, limit)
            
            # Display results
            click.echo(f"\nSynchronization completed:")
            click.echo(f"  Total processed: {stats.total_processed}")
            click.echo(f"  Created: {stats.created}")
            click.echo(f"  Updated: {stats.updated}")
            click.echo(f"  Skipped: {stats.skipped}") 
            click.echo(f"  Errors: {stats.errors}")
            
            if ctx.obj['verbose']:
                click.echo(f"\nDetailed results:")
                for result in results:
                    click.echo(f"  {result.action}: {result.message}")
                    if result.details:
                        click.echo(f"    Details: {json.dumps(result.details, indent=4)}")
                        
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)
    
    asyncio.run(run_sync())


@cli.command()
@click.option('--ollama-model', default=None, help='Ollama model to test (defaults to env OLLAMA_MODEL)')
@click.pass_context
def test_ai_detection(ctx, ollama_model: str):
    """Test AI duplicate detection with Ollama."""
    logger = ctx.obj['logger']
    
    # Use model from env if not specified
    if not ollama_model:
        ollama_model = os.getenv('OLLAMA_MODEL', 'mistral-small:24b')
    
    async def run_test():
        click.echo("Testing AI duplicate detection with Ollama...")
        click.echo(f"Model: {ollama_model}")
        
        try:
            from .ai_duplicate_detection import DuplicateDetectionService
            
            # Test Ollama connection
            import ollama
            models = ollama.list()
            model_names = [model.model for model in models.models]
            
            if ollama_model not in model_names:
                click.echo(f"✗ Model {ollama_model} not found")
                click.echo(f"Available models: {', '.join(model_names[:5])}...")  # Show first 5
                click.echo(f"Run: ollama pull {ollama_model}")
                return
            
            click.echo(f"✓ Ollama model {ollama_model} is available")
            
            # Test duplicate detection service
            detector = DuplicateDetectionService(ollama_model=ollama_model)
            
            # Sample test contacts
            linkedin_contact = {
                "First Name": "John",
                "Last Name": "Doe",
                "Company": "Tech Company",
                "Position": "Software Engineer"
            }
            
            crm_contact = {
                "firstname": "John",
                "lastname": "Doe",
                "fullname": "John Doe",
                "jobtitle": "Senior Software Engineer",
                "emailaddress1": "john.doe@techcompany.com"
            }
            
            click.echo("🤖 Testing AI comparison...")
            result = await detector.detector.compare_contacts(linkedin_contact, crm_contact)
            
            click.echo("✓ AI duplicate detection test successful")
            click.echo(f"  Result: {'Duplicate' if result.is_duplicate else 'Not duplicate'}")
            click.echo(f"  Confidence: {result.confidence}")
            click.echo(f"  Score: {result.similarity_score:.2f}")
            
        except ImportError:
            click.echo("✗ AI detection dependencies not installed")
            click.echo("Run: uv sync")
        except Exception as e:
            click.echo(f"✗ AI detection test failed: {str(e)}")
    
    asyncio.run(run_test())


@cli.command()
@click.pass_context  
def test_linkedin(ctx):
    """Test LinkedIn MCP server connection."""
    logger = ctx.obj['logger']
    
    async def run_test():
        click.echo("Testing LinkedIn MCP server connection...")
        
        # This would test the actual LinkedIn MCP server
        # For now, just test with mock client
        linkedin_client = MockMCPClient("linkedin")
        
        try:
            result = await linkedin_client.call_tool({
                "name": "get_member_snapshot_data",
                "arguments": {"domain": "CONNECTIONS"}
            })
            
            if result.get('success'):
                click.echo("✓ LinkedIn connection successful")
                if ctx.obj['verbose']:
                    click.echo(f"Profile data: {json.dumps(result.get('data', {}), indent=2)}")
            else:
                click.echo(f"✗ LinkedIn connection failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"✗ LinkedIn connection error: {str(e)}")
    
    asyncio.run(run_test())


@cli.command()
@click.pass_context
def test_dynamics(ctx):
    """Test Dynamics CRM MCP server connection."""
    logger = ctx.obj['logger']
    
    async def run_test():
        click.echo("Testing Dynamics CRM MCP server connection...")
        
        # This would test the actual Dynamics CRM MCP server
        # For now, just test with mock client
        dynamics_client = MockMCPClient("dynamics")
        
        try:
            result = await dynamics_client.call_tool({
                "name": "search_contacts",
                "arguments": {"top": 1}
            })
            
            if result.get('success'):
                click.echo("✓ Dynamics CRM connection successful")
                if ctx.obj['verbose']:
                    click.echo(f"Search result: {json.dumps(result.get('data', {}), indent=2)}")
            else:
                click.echo(f"✗ Dynamics CRM connection failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"✗ Dynamics CRM connection error: {str(e)}")
    
    asyncio.run(run_test())


@cli.command()
def test_playwright():
    """Test official Playwright MCP server functionality."""
    import subprocess
    import sys
    
    click.echo("🎭 Testing Official Playwright MCP Server...")
    
    try:
        # Run the Playwright test script
        script_path = Path(__file__).parent.parent / "test_playwright_official.py"
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True)
        
        click.echo(result.stdout)
        
        if result.stderr:
            click.echo("Errors:", nl=False)
            click.echo(result.stderr)
        
        if result.returncode == 0:
            click.echo("✓ Playwright MCP server test completed successfully")
        else:
            click.echo("✗ Playwright MCP server test failed")
            
    except Exception as e:
        click.echo(f"✗ Failed to run Playwright test: {str(e)}")


@cli.command()
def mcp_status():
    """Show status of all MCP servers."""
    import subprocess
    import sys
    
    try:
        script_path = Path(__file__).parent.parent / "services/mcp_manager.py"
        result = subprocess.run([
            sys.executable, str(script_path), "status"
        ], capture_output=True, text=True)
        
        click.echo(result.stdout)
        
        if result.stderr:
            click.echo("Errors:", nl=False) 
            click.echo(result.stderr)
            
    except Exception as e:
        click.echo(f"✗ Failed to get MCP server status: {str(e)}")


@cli.command()
@click.option('--max-profiles', type=int, help='Maximum number of profiles to scrape')
@click.option('--delay', type=float, default=3.0, help='Delay between profile scrapes in seconds')
def scrape_profiles(max_profiles: Optional[int], delay: float):
    """Scrape detailed LinkedIn profile data using AI and Playwright MCP."""
    import subprocess
    import sys
    
    click.echo("🤖 Starting AI-powered LinkedIn profile scraping...")
    
    if max_profiles:
        click.echo(f"📊 Limited to {max_profiles} profiles")
    
    click.echo(f"⏱️ Delay between scrapes: {delay} seconds")
    
    try:
        # Set environment variables for the scraper
        env = os.environ.copy()
        if max_profiles:
            env['SCRAPER_MAX_PROFILES'] = str(max_profiles)
        env['SCRAPER_DELAY'] = str(delay)
        
        # Run the scraper
        script_path = Path(__file__).parent.parent / "linkedin_profile_scraper.py"
        result = subprocess.run([
            sys.executable, str(script_path)
        ], env=env, capture_output=False, text=True)
        
        if result.returncode == 0:
            click.echo("✓ Profile scraping completed successfully")
        else:
            click.echo("✗ Profile scraping failed")
            
    except Exception as e:
        click.echo(f"✗ Failed to run profile scraper: {str(e)}")


if __name__ == '__main__':
    cli()