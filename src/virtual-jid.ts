/**
 * Virtual JID helpers for multi-agent fan-out.
 *
 * A virtual JID is a real channel JID with an `::agent-id` suffix:
 *   slack:C123::bug-reporter  →  real JID: slack:C123
 *
 * Each virtual JID maps to a separate agent (own session, memory, folder).
 * Messages are stored under the real JID; the virtual JID is used as the
 * cursor/group key so each agent has independent state.
 */

/** Extract the real channel JID from a (possibly virtual) JID. */
export function realJid(jid: string): string {
  const idx = jid.indexOf('::');
  return idx === -1 ? jid : jid.slice(0, idx);
}

/** Check if a JID is a virtual agent JID (contains `::`). */
export function isVirtualJid(jid: string): boolean {
  return jid.includes('::');
}

/**
 * Build a trigger regex from a group's trigger string.
 * e.g. "@BugReporter" → /^@BugReporter\b/i
 */
export function buildTriggerPattern(trigger: string): RegExp {
  const escaped = trigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`^${escaped}\\b`, 'i');
}
