/**
 * In-memory + session storage of detected media per tab.
 */

import type { DetectedMedia, Platform, TabMediaState } from "../shared/types";
import { STORAGE_KEYS } from "../shared/types";

const memory = new Map<number, TabMediaState>();

export async function upsertTabMedia(input: {
  tabId: number;
  pageUrl: string;
  platform: Platform;
  items: DetectedMedia[];
  replace?: boolean;
}): Promise<TabMediaState> {
  const prev = memory.get(input.tabId);
  const merged = mergeItems(
    input.replace ? [] : (prev?.items ?? []),
    input.items,
  );

  const state: TabMediaState = {
    tabId: input.tabId,
    pageUrl: input.pageUrl,
    platform: input.platform,
    items: merged,
    updatedAt: Date.now(),
  };

  memory.set(input.tabId, state);
  await persist(input.tabId, state);
  return state;
}

export async function getTabMedia(tabId: number): Promise<TabMediaState | null> {
  const cached = memory.get(tabId);
  if (cached) {
    return cached;
  }
  const all = await readAll();
  const state = all[String(tabId)] ?? null;
  if (state) {
    memory.set(tabId, state);
  }
  return state;
}

export async function clearTabMedia(tabId: number): Promise<void> {
  memory.delete(tabId);
  const all = await readAll();
  delete all[String(tabId)];
  await chrome.storage.session.set({ [STORAGE_KEYS.mediaByTab]: all });
}

function mergeItems(
  existing: DetectedMedia[],
  incoming: DetectedMedia[],
): DetectedMedia[] {
  const map = new Map<string, DetectedMedia>();
  for (const item of existing) {
    map.set(item.id, item);
  }
  for (const item of incoming) {
    const prev = map.get(item.id);
    map.set(item.id, prev ? { ...prev, ...item, foundAt: prev.foundAt } : item);
  }
  return [...map.values()].sort((a, b) => b.foundAt - a.foundAt);
}

async function persist(tabId: number, state: TabMediaState): Promise<void> {
  const all = await readAll();
  all[String(tabId)] = state;
  await chrome.storage.session.set({ [STORAGE_KEYS.mediaByTab]: all });
}

async function readAll(): Promise<Record<string, TabMediaState>> {
  const stored = await chrome.storage.session.get(STORAGE_KEYS.mediaByTab);
  const value = stored[STORAGE_KEYS.mediaByTab];
  if (value && typeof value === "object") {
    return value as Record<string, TabMediaState>;
  }
  return {};
}
