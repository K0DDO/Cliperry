import type { Platform } from "./types";

const PLATFORM_HOSTS: Array<{ platform: Platform; match: RegExp }> = [
  { platform: "youtube", match: /(^|\.)youtube\.com$|(^|\.)youtu\.be$/i },
  { platform: "tiktok", match: /(^|\.)tiktok\.com$/i },
  { platform: "instagram", match: /(^|\.)instagram\.com$/i },
  { platform: "twitter", match: /(^|\.)twitter\.com$|(^|\.)x\.com$/i },
];

export function detectPlatform(url: string): Platform {
  try {
    const host = new URL(url).hostname.replace(/^www\./i, "");
    for (const entry of PLATFORM_HOSTS) {
      if (entry.match.test(host)) {
        return entry.platform;
      }
    }
  } catch {
    return "unknown";
  }
  return "unknown";
}

export function isSupportedUrl(url: string): boolean {
  return detectPlatform(url) !== "unknown";
}
