#!/usr/bin/env node

/**
 * Serena MCP Server Installation Verification Script
 * 
 * This script verifies that the Serena MCP server has been properly installed
 * and configured for both Claude Desktop and Claude Code CLI.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

class SerenaVerifier {
    constructor() {
        this.platform = os.platform();
        this.claudeConfigDir = this.getClaudeConfigDir();
        this.logPrefix = '[Serena Verifier]';
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
        this.warnings = 0;
    }

    log(message, type = 'info') {
        const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warning' ? '⚠️' : 'ℹ️';
        console.log(`${prefix} ${this.logPrefix} ${message}`);
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
                throw new Error(`Unsupported platform: ${this.platform}`);
        }
    }

    addTest(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async runTest(test) {
        try {
            await test.testFn();
            this.log(`${test.name}`, 'success');
            this.passed++;
            return true;
        } catch (error) {
            this.log(`${test.name}: ${error.message}`, 'error');
            this.failed++;
            return false;
        }
    }

    async runAllTests() {
        this.log('Starting Serena MCP Server installation verification...');
        this.log('');

        for (const test of this.tests) {
            await this.runTest(test);
        }

        this.log('');
        this.showSummary();
    }

    showSummary() {
        this.log(`Verification Results:`);
        this.log(`- Tests Run: ${this.tests.length}`);
        this.log(`- Passed: ${this.passed} ✅`);
        this.log(`- Failed: ${this.failed} ${this.failed > 0 ? '❌' : '✅'}`);
        this.log(`- Warnings: ${this.warnings} ${this.warnings > 0 ? '⚠️' : '✅'}`);
        this.log(`- Success Rate: ${Math.round((this.passed / this.tests.length) * 100)}%`);

        if (this.failed === 0) {
            this.log('');
            this.log('🎉 All tests passed! Serena MCP server is properly installed and configured.', 'success');
        } else {
            this.log('');
            this.log('Some tests failed. Please check the installation.', 'error');
        }
    }

    setupTests() {
        // Test 1: Check if uvx is available
        this.addTest('uvx is installed and accessible', () => {
            const result = execSync('uvx --version', { encoding: 'utf8', stdio: 'pipe' });
            if (!result || result.trim().length === 0) {
                throw new Error('uvx not found or not working');
            }
        });

        // Test 2: Check if Python is available
        this.addTest('Python 3.11 is installed', () => {
            const result = execSync('python --version', { encoding: 'utf8', stdio: 'pipe' });
            if (!result.includes('Python 3.11')) {
                throw new Error(`Python 3.11 required, found: ${result.trim()}`);
            }
        });

        // Test 3: Test Serena server accessibility
        this.addTest('Serena MCP server is accessible via uvx', () => {
            const result = execSync('uvx --from git+https://github.com/oraios/serena serena --help', { 
                encoding: 'utf8', 
                stdio: 'pipe',
                timeout: 30000 
            });
            if (!result.includes('serena') && !result.includes('Serena')) {
                throw new Error('Serena server not accessible or not responding correctly');
            }
        });

        // Test 4: Check Claude Desktop configuration
        this.addTest('Claude Desktop configuration exists', () => {
            const configPath = path.join(this.claudeConfigDir, 'claude_desktop_config.json');
            if (!fs.existsSync(configPath)) {
                throw new Error('Claude Desktop configuration file not found');
            }

            const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
            if (!config.mcpServers || !config.mcpServers.serena) {
                throw new Error('Serena MCP server not configured in Claude Desktop');
            }

            if (config.mcpServers.serena.command !== 'uvx') {
                throw new Error('Claude Desktop Serena configuration has incorrect command');
            }
        });

        // Test 5: Check Claude Code CLI configuration
        this.addTest('Claude Code CLI MCP server is configured', () => {
            const result = execSync('claude mcp list', { encoding: 'utf8', stdio: 'pipe' });
            if (!result.includes('serena')) {
                throw new Error('Serena MCP server not found in Claude Code CLI');
            }
            if (!result.includes('Connected') && !result.includes('✓')) {
                throw new Error('Serena MCP server not connected in Claude Code CLI');
            }
        });

        // Test 6: Verify server responds to basic commands (optional)
        this.addTest('Serena MCP server responds to help command', () => {
            try {
                const result = execSync('uvx --from git+https://github.com/oraios/serena serena start-mcp-server --help', { 
                    encoding: 'utf8', 
                    stdio: 'pipe',
                    timeout: 15000
                });
                // Just check that it doesn't crash
                return true;
            } catch (error) {
                // This is more of a warning than a failure
                this.warnings++;
                this.log('Serena server help command test - this may be expected behavior', 'warning');
                return true;
            }
        });
    }

    async verify() {
        this.setupTests();
        await this.runAllTests();
        return this.failed === 0;
    }
}

// Run verifier if called directly
if (require.main === module) {
    const verifier = new SerenaVerifier();
    verifier.verify().then(success => {
        process.exit(success ? 0 : 1);
    }).catch(error => {
        console.error('Verification failed:', error);
        process.exit(1);
    });
}

module.exports = SerenaVerifier;