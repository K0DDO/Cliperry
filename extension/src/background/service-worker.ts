/**
 * Cliperry service worker (Manifest V3).
 * Event hub between content scripts and popup.
 */

import type { CliperryEvent } from "../shared/events";
import { onEvent, sendEvent, sendToTab } from "../shared/messaging";
import { detectPlatform } from "../shared/platform";
import { getOrCreateDeviceId } from "../shared/storage";
import {
  clearTabMedia,
  getTabMedia,
  upsertTabMedia,
} from "./media-store";

chrome.runtime.onInstalled.addListener(async (details) => {
  await getOrCreateDeviceId();
  console.info("[Cliperry] installed", details.reason);
});

chrome.tabs.onRemoved.addListener((tabId) => {
  void clearTabMedia(tabId);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading" && changeInfo.url) {
    void clearTabMedia(tabId);
    void updateBadge(tabId, 0);
  }
});

onEvent(async (event, sender) => {
  switch (event.type) {
    case "PING":
      return { type: "PONG", source: "background" };

    case "GET_PAGE_URL":
      return resolveActiveTabUrl();

    case "MEDIA_FOUND": {
      const tabId = sender.tab?.id;
      if (tabId == null) {
        return { type: "ERROR", message: "MEDIA_FOUND without tab", code: "NO_TAB" };
      }
      const state = await upsertTabMedia({
        tabId,
        pageUrl: event.pageUrl,
        platform: event.platform,
        items: event.items,
        replace: event.replace ?? true,
      });
      await updateBadge(tabId, state.items.length);
      // Fan-out to popup (if open).
      await sendEvent({ type: "MEDIA_UPDATED", state });
      return { type: "MEDIA_STATE", state };
    }

    case "GET_MEDIA": {
      const tabId = event.tabId ?? (await getActiveTabId());
      if (tabId == null) {
        return { type: "MEDIA_STATE", state: null };
      }
      const state = await getTabMedia(tabId);
      return { type: "MEDIA_STATE", state };
    }

    case "REQUEST_SCAN": {
      const tabId = await getActiveTabId();
      if (tabId == null) {
        return { type: "ERROR", message: "No active tab", code: "NO_TAB" };
      }
      const response = await sendToTab(tabId, { type: "SCAN_NOW" });
      if (response?.type === "MEDIA_FOUND") {
        const state = await upsertTabMedia({
          tabId,
          pageUrl: response.pageUrl,
          platform: response.platform,
          items: response.items,
          replace: true,
        });
        await updateBadge(tabId, state.items.length);
        await sendEvent({ type: "MEDIA_UPDATED", state });
        return { type: "MEDIA_STATE", state };
      }
      const existing = await getTabMedia(tabId);
      return { type: "MEDIA_STATE", state: existing };
    }

    default:
      return;
  }
});

/** Capture mp4 / m3u8 network responses as a secondary signal. */
chrome.webRequest.onCompleted.addListener(
  (details) => {
    if (details.tabId < 0) {
      return;
    }
    const url = details.url;
    if (!/\.m3u8(?:$|\?|#)/i.test(url) && !/\.mp4(?:$|\?|#)/i.test(url)) {
      return;
    }
    const kind = /\.m3u8(?:$|\?|#)/i.test(url) ? "m3u8" : "mp4";
    void (async () => {
      const tab = await chrome.tabs.get(details.tabId).catch(() => null);
      const pageUrl = tab?.url ?? details.initiator ?? url;
      const platform = detectPlatform(pageUrl);
      const id = `net_${simpleHash(url)}`;
      const state = await upsertTabMedia({
        tabId: details.tabId,
        pageUrl,
        platform,
        replace: false,
        items: [
          {
            id,
            url,
            kind,
            source: "network",
            pageUrl,
            platform,
            title: tab?.title,
            foundAt: Date.now(),
          },
        ],
      });
      await updateBadge(details.tabId, state.items.length);
      await sendEvent({ type: "MEDIA_UPDATED", state });
    })();
  },
  {
    urls: ["<all_urls>"],
    types: ["xmlhttprequest", "media", "other", "object"],
  },
);

async function resolveActiveTabUrl(): Promise<CliperryEvent> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab?.url ?? "";
  return {
    type: "PAGE_URL",
    url,
    platform: url ? detectPlatform(url) : "unknown",
  };
}

async function getActiveTabId(): Promise<number | null> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.id ?? null;
}

async function updateBadge(tabId: number, count: number): Promise<void> {
  const text = count > 0 ? String(Math.min(count, 99)) : "";
  await chrome.action.setBadgeText({ tabId, text });
  await chrome.action.setBadgeBackgroundColor({
    tabId,
    color: "#c4294a",
  });
}

function simpleHash(value: string): string {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash.toString(16);
}

console.info("[Cliperry] background ready");
