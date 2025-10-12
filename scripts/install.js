#!/usr/bin/env node

/**
 * Serena MCP Server Installation Script
 * 
 * This script automatically installs and configures the Serena MCP server
 * for use with Claude Desktop and Claude Code CLI. It handles cross-platform
 * installation, dependency checking, and configuration setup.
 * 
 * Usage: node scripts/install.js [--config=path/to/config.json]
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync, spawn } = require('child_process');

class SerenaInstaller {
    constructor() {
        this.platform = os.platform();
        this.projectRoot = path.dirname(__dirname);
        this.config = null;
        this.claudeConfigDir = this.getClaudeConfigDir();
        this.logPrefix = '[Serena Installer]';
    }

    log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
        console.log(`${prefix} ${this.logPrefix} ${message}`);
    }

    error(message, exit = true) {
        this.log(message, 'error');
        if (exit) process.exit(1);
    }

    success(message) {
        this.log(message, 'success');
    }

    getClaudeConfigDir() {
        switch (this.platform) {
            case 'win32':
                return path.join(os.homedir(), 'AppData', 'Roaming', 'Claude');
            case 'darwin':
                return path.join(os.homedir(), 'Library', 'Application Support', 'Claude');
            case 'linux':
                return path.join(os.homedir(), '.config', 'claude');
            default:
                this.error(`Unsupported platform: ${this.platform}`);
        }
    }

    loadConfig() {
        const configArg = process.argv.find(arg => arg.startsWith('--config='));
        const configPath = configArg 
            ? configArg.split('=')[1]
            : path.join(this.projectRoot, 'scripts', 'install-config.json');

        if (!fs.existsSync(configPath)) {
            this.error(`Configuration file not found: ${configPath}`);
        }

        try {
            this.config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
            this.log(`Loaded configuration from: ${configPath}`);
        } catch (error) {
            this.error(`Failed to parse configuration file: ${error.message}`);
        }
    }

    checkSystemDependencies() {
        this.log('Checking system dependencies...');

        // Check Python version (uvx handles Python requirements automatically)
        try {
            const pythonVersion = execSync('python --version', { encoding: 'utf8', stdio: 'pipe' }).trim();
            this.log(`System Python version: ${pythonVersion}`);
            this.log('Note: uvx will manage Python 3.11 requirements automatically for Serena ✓');
        } catch (error) {
            this.log('Python not found in system PATH, but uvx will handle Python requirements ✓');
        }

        // Check for uvx
        try {
            const uvxVersion = execSync('uvx --version', { encoding: 'utf8', stdio: 'pipe' }).trim();
            this.log(`uvx version: ${uvxVersion} ✓`);
        } catch (error) {
            this.error('uvx is not installed. Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh');
        }

        this.success('System dependencies check completed');
    }

    testSerenaServer() {
        this.log('Testing Serena MCP server...');

        try {
            // Test server startup with --help flag
            const result = execSync('uvx --from git+https://github.com/RoscoeTheDog/serena serena --help', {
                encoding: 'utf8',
                timeout: 30000,
                stdio: 'pipe'
            });

            if (result.includes('Serena') || result.includes('serena')) {
                this.success('Serena MCP server test completed successfully');
            } else {
                throw new Error('Unexpected server response');
            }
        } catch (error) {
            this.log(`Warning: Serena server test failed: ${error.message}`, 'error');
            this.log('This may not be critical if the server can be reached via uvx');
        }
    }

    createClaudeConfig() {
        this.log('Creating Claude Desktop and Claude Code CLI configuration...');

        // Configure Claude Desktop
        this.configureClaudeDesktop();
        
        // Configure Claude Code CLI
        this.configureClaudeCodeCLI();
    }

    configureClaudeDesktop() {
        this.log('Configuring Claude Desktop...');

        // Ensure Claude config directory exists
        if (!fs.existsSync(this.claudeConfigDir)) {
            fs.mkdirSync(this.claudeConfigDir, { recursive: true });
            this.log(`Created Claude config directory: ${this.claudeConfigDir}`);
        }

        const configPath = path.join(this.claudeConfigDir, 'claude_desktop_config.json');
        
        // Create Serena server configuration
        const claudeConfig = {
            mcpServers: {
                "serena": {
                    command: "uvx",
                    args: [
                        "--from", "git+https://github.com/RoscoeTheDog/serena",
                        "serena", "start-mcp-server",
                        "--context", "ide-assistant"
                    ]
                }
            }
        };

        // Backup existing config if it exists
        if (fs.existsSync(configPath)) {
            const backupPath = `${configPath}.backup.${Date.now()}`;
            fs.copyFileSync(configPath, backupPath);
            this.log(`Backed up existing configuration to: ${backupPath}`);
        }

        // Write new configuration
        try {
            fs.writeFileSync(configPath, JSON.stringify(claudeConfig, null, 2));
            this.success(`Claude Desktop configuration created: ${configPath}`);
        } catch (error) {
            this.error(`Failed to write Claude Desktop configuration: ${error.message}`);
        }
    }

    configureClaudeCodeCLI() {
        this.log('Configuring Claude Code CLI...');

        try {
            // First, try to remove existing server if it exists
            try {
                this.log('Checking for existing Claude Code CLI MCP server...');
                execSync('claude mcp remove serena -s user', { 
                    stdio: 'pipe',
                    encoding: 'utf8'
                });
                this.log('Removed existing MCP server configuration');
            } catch (removeError) {
                // It's fine if removal fails (server might not exist)
                this.log('No existing MCP server found (expected for fresh installation)');
            }

            // Build the claude mcp add command for Serena
            const command = 'claude mcp add serena uvx -- --from git+https://github.com/RoscoeTheDog/serena serena start-mcp-server --context ide-assistant -s user';

            // Execute the command to add MCP server to Claude Code CLI
            this.log('Adding Serena MCP server to Claude Code CLI with user scope...');
            execSync(command, { 
                stdio: this.config.verbose ? 'inherit' : 'pipe',
                encoding: 'utf8'
            });

            this.success('Claude Code CLI configuration completed');
        } catch (error) {
            if (error.message.includes('already exists')) {
                this.success('Claude Code CLI MCP server already configured');
            } else {
                this.log(`Warning: Failed to configure Claude Code CLI: ${error.message}`, 'error');
                this.log('You may need to manually run: claude mcp add serena uvx -- --from git+https://github.com/RoscoeTheDog/serena serena start-mcp-server --context ide-assistant -s user');
            }
        }
    }

    async install() {
        try {
            this.log('Starting Serena MCP Server installation...');
            
            // Step 1: Load configuration
            this.loadConfig();
            
            // Step 2: Check system dependencies
            this.checkSystemDependencies();
            
            // Step 3: Test Serena server
            this.testSerenaServer();
            
            // Step 4: Create Claude configuration
            this.createClaudeConfig();
            
            this.success('Installation completed successfully!');
            this.log('');
            this.log('Configuration completed for:');
            this.log('✅ Claude Desktop - Restart Claude Desktop to load the MCP server');
            this.log('✅ Claude Code CLI - MCP server configured globally with user scope');
            this.log('');
            this.log('Next steps:');
            this.log('1. Restart Claude Desktop to load the new MCP server');
            this.log('2. Test Claude Code CLI: Open any terminal and run "claude mcp list"');
            this.log('3. The Serena server will be available for semantic code analysis');
            this.log('4. Run "node scripts/verify.js" to verify the installation (if verify script exists)');
            this.log('');
            
        } catch (error) {
            this.error(`Installation failed: ${error.message}`);
        }
    }
}

// Run installer if called directly
if (require.main === module) {
    const installer = new SerenaInstaller();
    installer.install().catch(error => {
        console.error('Installation failed:', error);
        process.exit(1);
    });
}

module.exports = SerenaInstaller;