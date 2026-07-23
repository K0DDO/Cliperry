/**
 * Content script — detects video/source/media URLs and reports to background.
 */

import { createMediaWatcher, scanPageMedia } from "./detector";
import { detectPlatform } from "../shared/platform";
import type { DetectedMedia } from "../shared/types";
import { onEvent, sendEvent } from "../shared/messaging";

const ROOT_ID = "cliperry-content-root";
let lastSentSignature = "";

function reportMedia(items: DetectedMedia[], replace = true): void {
  const signature = items.map((item) => item.id).sort().join("|");
  if (replace && signature === lastSentSignature) {
    return;
  }
  lastSentSignature = signature;

  const pageUrl = window.location.href;
  const platform = detectPlatform(pageUrl);

  void sendEvent({
    type: "MEDIA_FOUND",
    pageUrl,
    platform,
    items,
    replace,
  });

  updateHint(items.length, platform);
}

function updateHint(count: number, platform: string): void {
  let root = document.getElementById(ROOT_ID);
  if (!root) {
    root = document.createElement("div");
    root.id = ROOT_ID;
    root.className = "cliperry-hint";
    document.documentElement.appendChild(root);
  }

  root.setAttribute("data-platform", platform);
  root.innerHTML = `
    <span class="cliperry-hint__mark" aria-hidden="true">🍓</span>
    <span class="cliperry-hint__text">${hintText(count, platform)}</span>
  `;
  root.classList.add("cliperry-hint--visible");
}

function hintText(count: number, platform: string): string {
  const label = labelFor(platform);
  if (count <= 0) {
    return `Cliperry · ${label}`;
  }
  return `Cliperry · найдено ${count} · ${label}`;
}

function labelFor(platform: string): string {
  switch (platform) {
    case "youtube":
      return "YouTube";
    case "tiktok":
      return "TikTok";
    case "instagram":
      return "Instagram";
    case "twitter":
      return "Twitter / X";
    default:
      return platform;
  }
}

onEvent((event) => {
  if (event.type === "PING") {
    return { type: "PONG", source: "content" };
  }

  if (event.type === "GET_PAGE_URL") {
    return {
      type: "PAGE_URL",
      url: window.location.href,
      platform: detectPlatform(window.location.href),
    };
  }

  if (event.type === "SCAN_NOW") {
    const items = scanPageMedia();
    reportMedia(items, true);
    return {
      type: "MEDIA_FOUND",
      pageUrl: window.location.href,
      platform: detectPlatform(window.location.href),
      items,
      replace: true,
    };
  }

  return;
});

const stopWatcher = createMediaWatcher((items) => {
  reportMedia(items, true);
});

window.addEventListener("pagehide", () => {
  stopWatcher();
});

console.info("[Cliperry] content script ready", window.location.hostname);
