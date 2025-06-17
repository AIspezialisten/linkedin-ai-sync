"""
MCP Server Manager for running multiple MCP servers in the container.

This service starts and manages:
- LinkedIn MCP Server
- Microsoft Dynamics CRM MCP Server  
- Playwright MCP Server
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import os
import json
import time


class MCPServerManager:
    """Manages multiple MCP servers running in the background."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.servers: Dict[str, subprocess.Popen] = {}
        self.config_file = Path("/app/data/mcp_servers.json")
        self.running = False
        
        # Default server configurations
        self.server_configs = {
            "linkedin": {
                "name": "LinkedIn MCP Server",
                "command": ["uv", "run", "python", "-m", "mcp_servers.linkedin"],
                "port": 8001,
                "auto_restart": True,
                "enabled": True
            },
            "dynamics_crm": {
                "name": "Microsoft Dynamics CRM MCP Server", 
                "command": ["uv", "run", "python", "-m", "mcp_servers.dynamics_crm"],
                "port": 8002,
                "auto_restart": True,
                "enabled": True
            },
            "playwright": {
                "name": "Playwright MCP Server (LinkedIn)",
                "command": ["uv", "run", "python", "-m", "mcp_servers.playwright"],
                "port": 8003,
                "auto_restart": True,
                "enabled": True
            }
        }
    
    def load_config(self):
        """Load server configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults
                for server_id, config in loaded_config.items():
                    if server_id in self.server_configs:
                        self.server_configs[server_id].update(config)
                
                self.logger.info("Loaded MCP server configuration")
            else:
                self.save_config()
                
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.server_configs, f, indent=2)
                
            self.logger.info("Saved MCP server configuration")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
    
    async def start_server(self, server_id: str) -> bool:
        """Start a specific MCP server."""
        if server_id not in self.server_configs:
            self.logger.error(f"Unknown server: {server_id}")
            return False
        
        config = self.server_configs[server_id]
        
        if not config.get("enabled", True):
            self.logger.info(f"Server {server_id} is disabled")
            return False
        
        if server_id in self.servers and self.servers[server_id].poll() is None:
            self.logger.info(f"Server {server_id} is already running")
            return True
        
        try:
            self.logger.info(f"Starting {config['name']}...")
            
            # Set environment variables
            env = os.environ.copy()
            env["MCP_SERVER_PORT"] = str(config.get("port", 8000))
            
            # Start the server process
            process = subprocess.Popen(
                config["command"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd="/app"
            )
            
            # Wait a moment to check if the process started successfully
            await asyncio.sleep(1)
            
            if process.poll() is None:  # Process is still running
                self.servers[server_id] = process
                self.logger.info(f"✅ {config['name']} started successfully (PID: {process.pid})")
                return True
            else:
                # Process died immediately
                stdout, stderr = process.communicate()
                self.logger.error(f"❌ {config['name']} failed to start:")
                self.logger.error(f"  stdout: {stdout.decode()}")
                self.logger.error(f"  stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start {server_id}: {str(e)}")
            return False
    
    async def stop_server(self, server_id: str) -> bool:
        """Stop a specific MCP server."""
        if server_id not in self.servers:
            self.logger.info(f"Server {server_id} is not running")
            return True
        
        try:
            process = self.servers[server_id]
            
            self.logger.info(f"Stopping {self.server_configs[server_id]['name']}...")
            
            # Try graceful shutdown first
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process(process)),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown failed
                self.logger.warning(f"Force killing {server_id}")
                process.kill()
                await asyncio.create_task(self._wait_for_process(process))
            
            del self.servers[server_id]
            self.logger.info(f"✅ {self.server_configs[server_id]['name']} stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop {server_id}: {str(e)}")
            return False
    
    async def _wait_for_process(self, process: subprocess.Popen):
        """Wait for a process to finish."""
        while process.poll() is None:
            await asyncio.sleep(0.1)
    
    async def restart_server(self, server_id: str) -> bool:
        """Restart a specific MCP server."""
        self.logger.info(f"Restarting {server_id}...")
        
        await self.stop_server(server_id)
        await asyncio.sleep(2)  # Brief pause
        return await self.start_server(server_id)
    
    async def start_all_servers(self):
        """Start all enabled MCP servers."""
        self.logger.info("🚀 Starting all MCP servers...")
        
        results = []
        for server_id in self.server_configs.keys():
            result = await self.start_server(server_id)
            results.append((server_id, result))
        
        # Log summary
        successful = [s for s, r in results if r]
        failed = [s for s, r in results if not r]
        
        self.logger.info(f"✅ Successfully started: {', '.join(successful) if successful else 'none'}")
        if failed:
            self.logger.error(f"❌ Failed to start: {', '.join(failed)}")
        
        return len(successful) > 0
    
    async def stop_all_servers(self):
        """Stop all running MCP servers."""
        self.logger.info("🛑 Stopping all MCP servers...")
        
        for server_id in list(self.servers.keys()):
            await self.stop_server(server_id)
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get status of all servers."""
        status = {}
        
        for server_id, config in self.server_configs.items():
            is_running = (
                server_id in self.servers and 
                self.servers[server_id].poll() is None
            )
            
            status[server_id] = {
                "name": config["name"],
                "enabled": config.get("enabled", True),
                "running": is_running,
                "pid": self.servers[server_id].pid if is_running else None,
                "port": config.get("port"),
                "auto_restart": config.get("auto_restart", True)
            }
        
        return status
    
    async def health_check(self):
        """Perform health check and restart failed servers."""
        for server_id, config in self.server_configs.items():
            if not config.get("enabled", True):
                continue
            
            if not config.get("auto_restart", True):
                continue
            
            # Check if server should be running but isn't
            if server_id not in self.servers or self.servers[server_id].poll() is not None:
                self.logger.warning(f"Server {server_id} is not running, attempting restart...")
                await self.start_server(server_id)
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        self.logger.info("🔍 Starting MCP server monitoring loop...")
        
        while self.running:
            try:
                await self.health_check()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def run(self):
        """Main run method."""
        self.running = True
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Load configuration
            self.load_config()
            
            # Start all servers
            await self.start_all_servers()
            
            # Run monitoring loop
            await self.monitor_loop()
            
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
        finally:
            # Cleanup
            await self.stop_all_servers()
            self.logger.info("MCP Server Manager stopped")
    
    def print_status(self):
        """Print current server status."""
        status = self.get_server_status()
        
        print("🤖 MCP Server Status")
        print("==================")
        
        for server_id, info in status.items():
            status_icon = "🟢" if info["running"] else "🔴"
            enabled_text = "enabled" if info["enabled"] else "disabled"
            
            print(f"{status_icon} {info['name']}")
            print(f"   Status: {'Running' if info['running'] else 'Stopped'} ({enabled_text})")
            if info["running"]:
                print(f"   PID: {info['pid']}")
            if info["port"]:
                print(f"   Port: {info['port']}")
            print()


async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/app/data/mcp_manager.log', mode='a')
        ]
    )
    
    manager = MCPServerManager()
    
    # Check if we should just print status
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        manager.load_config()
        manager.print_status()
        return
    
    # Run the manager
    await manager.run()


if __name__ == "__main__":
    asyncio.run(main())