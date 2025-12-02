#!/usr/bin/env node

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Get Python command (try python3 first, fallback to python)
const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

// Path to the MCP server script
const serverScript = join(projectRoot, 'openproject-mcp-fastmcp.py');

// Environment variables from Claude Desktop config
const env = {
  ...process.env,
  OPENPROJECT_URL: process.env.OPENPROJECT_API_URL || process.env.OPENPROJECT_URL,
  OPENPROJECT_API_KEY: process.env.OPENPROJECT_API_KEY,
  OPENPROJECT_PROXY: process.env.OPENPROJECT_PROXY || '',
  LOG_LEVEL: process.env.LOG_LEVEL || 'INFO',
};

// Spawn Python process
const pythonProcess = spawn(pythonCmd, [serverScript], {
  env,
  stdio: 'inherit',
  cwd: projectRoot,
});

// Handle process events
pythonProcess.on('error', (error) => {
  console.error('Failed to start OpenProject MCP server:', error.message);
  console.error('\nMake sure Python 3.10+ is installed and available in PATH.');
  console.error('You can install it from: https://www.python.org/downloads/');
  process.exit(1);
});

pythonProcess.on('exit', (code, signal) => {
  if (code !== 0 && code !== null) {
    console.error(`\nOpenProject MCP server exited with code ${code}`);
    process.exit(code);
  }
  if (signal) {
    console.error(`\nOpenProject MCP server was killed with signal ${signal}`);
    process.exit(1);
  }
});

// Forward signals
process.on('SIGINT', () => {
  pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  pythonProcess.kill('SIGTERM');
});
