import crypto from 'node:crypto';
type PackageManifest = { packages: any }; type McpServerDef = any;
function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, child]) => [key, canonicalize(child)]),
    );
  }
  return value;
}

export function packageDeclarationHash(manifest: PackageManifest): string {
  return packageSetHash(manifest.packages);
}

function packageSetHash(packages: PackageManifest['packages']): string {
  return crypto
    .createHash('sha256')
    .update(JSON.stringify(canonicalize(packages)))
    .digest('hex');
}
const PLACEHOLDER_RE = /\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

/** Every ${VAR} referenced anywhere in a def. */
export function referencedVars(def: McpServerDef): string[] {
  const found = new Set<string>();
  const scan = (v: string | undefined): void => {
    if (!v) return;
    for (const m of v.matchAll(PLACEHOLDER_RE)) found.add(m[1]);
  };
  scan(def.url);
  scan(def.command);
  def.args?.forEach(scan);
  Object.values(def.headers ?? {}).forEach(scan);
  Object.values(def.env ?? {}).forEach(scan);
  return [...found];
}

export interface ResolveResult {
  def: McpServerDef;
  /** Vars referenced but not found in the lookup table. */
  missing: string[];
}
function placeholderValue(vars: Record<string, string>, name: string): string | undefined { return Object.hasOwn(vars, name) ? vars[name] : undefined; }
/**
 * Substitute ${VAR} throughout a def. Unresolved vars are left as-is and
 * reported, so the caller can skip the server rather than inject a broken one.
 */
export function resolvePlaceholders(def: McpServerDef, vars: Record<string, string>): ResolveResult {
  const missing = new Set<string>();
  const lookup = (name: string): string | undefined => placeholderValue(vars, name);
  const sub = (v: string): string =>
    v.replace(PLACEHOLDER_RE, (whole, name: string) => {
      const val = lookup(name);
      if (val === undefined || val === '') {
        missing.add(name);
        return whole;
      }
      return val;
    });
  const subMap = (m: Record<string, string> | undefined): Record<string, string> | undefined =>
    m && Object.fromEntries(Object.entries(m).map(([k, v]) => [k, sub(v)]));

  return {
    def: {
      ...def,
      command: def.command ? sub(def.command) : undefined,
      args: def.args?.map(sub),
      url: def.url ? sub(def.url) : undefined,
      headers: subMap(def.headers),
      env: subMap(def.env),
    },
    missing: [...missing],
  };
}

// ─── Renderers ───────────────────────────────────────────────

export type McpJsonEntry = Record<string, unknown>;

function renderClaude(def: McpServerDef): McpJsonEntry {
  const e: McpJsonEntry = { type: def.transport };
  if (def.transport === 'stdio') {
    e.command = def.command;
    if (def.args?.length) e.args = def.args;
    if (def.env && Object.keys(def.env).length) e.env = def.env;
  } else {
    e.url = def.url;
    if (def.headers && Object.keys(def.headers).length) e.headers = def.headers;
  }
  return e;
}
/** Stable content hash of a rendered entry; drives idempotent rewrites. */
export function entryHash(rendered: unknown): string {
  return crypto.createHash('sha1').update(JSON.stringify(rendered)).digest('hex').slice(0, 16);
}
export { packageSetHash, renderClaude };
