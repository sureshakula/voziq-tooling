// _srt_resolve.mjs — Resolves bwrap command via @anthropic-ai/sandbox-runtime library.
// Called by sandbox.py. Reads config JSON from file (argv[1]), command string (argv[2]).
// Prints the shell-quoted bwrap command to stdout. Exits 0 on success, 1 on error.
//
// srt is installed globally (npm i -g). ESM resolution walks up from this file's
// directory, never reaching the global node_modules. We derive the path from the
// running Node binary instead.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const nodePrefix = dirname(dirname(process.execPath));
const srtEntry = join(nodePrefix, 'lib/node_modules/@anthropic-ai/sandbox-runtime/dist/index.js');
const { SandboxManager } = await import(pathToFileURL(srtEntry).href);

const configPath = process.argv[2];
const command = process.argv[3];

if (!configPath || !command) {
  process.stderr.write('usage: _srt_resolve.mjs <config.json> <command>\n');
  process.exit(1);
}

try {
  const config = JSON.parse(readFileSync(configPath, 'utf-8'));
  await SandboxManager.initialize(config);
  const wrapped = await SandboxManager.wrapWithSandbox(command, '/bin/bash', config);
  process.stdout.write(wrapped);
  await SandboxManager.reset();
} catch (err) {
  process.stderr.write(`srt-resolve error: ${err.message}\n`);
  process.exit(1);
}
