import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { logger } from './logger.js';

/**
 * Cache for SSM-fetched values to avoid repeated AWS calls within a session.
 * Keys are SSM parameter paths (e.g. "/tbg/shared/observability/GRAFANA_SA_TOKEN").
 */
const ssmCache = new Map<string, string>();

/**
 * Fetch a single SecureString parameter from AWS SSM Parameter Store.
 * Uses the aws CLI via execSync — inherits caller's AWS credentials.
 * Returns undefined if the fetch fails (e.g., no AWS creds, no permission,
 * parameter missing). Errors are logged but not thrown so callers can
 * fall back to .env gracefully.
 */
export function fetchSsmParameter(
  paramName: string,
  region: string = 'us-east-1',
): string | undefined {
  if (ssmCache.has(paramName)) {
    return ssmCache.get(paramName);
  }
  try {
    const stdout = execSync(
      `aws ssm get-parameter --name "${paramName}" --with-decryption --region "${region}" --query "Parameter.Value" --output text`,
      { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 10000 },
    );
    const value = stdout.trim();
    if (value && value !== 'None') {
      ssmCache.set(paramName, value);
      return value;
    }
  } catch (err) {
    logger.debug(
      { err, paramName },
      'SSM fetch failed — check aws CLI, credentials, or parameter name',
    );
  }
  return undefined;
}

/**
 * Parse the .env file and return values for the requested keys.
 * Does NOT load anything into process.env — callers decide what to
 * do with the values. This keeps secrets out of the process environment
 * so they don't leak to child processes.
 */
export function readEnvFile(keys: string[]): Record<string, string> {
  const envFile = path.join(process.cwd(), '.env');
  let content: string;
  try {
    content = fs.readFileSync(envFile, 'utf-8');
  } catch (err) {
    logger.debug({ err }, '.env file not found, using defaults');
    return {};
  }

  const result: Record<string, string> = {};
  const wanted = new Set(keys);

  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    if (!wanted.has(key)) continue;
    let value = trimmed.slice(eqIdx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (value) result[key] = value;
  }

  return result;
}
