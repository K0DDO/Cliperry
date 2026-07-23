/**
 * DOM + resource media detector (video / source / mp4 / m3u8).
 */

import { detectPlatform } from "../shared/platform";
import type { DetectedMedia, MediaKind, MediaSourceKind, Platform } from "../shared/types";

const MEDIA_URL_RE =
  /(?:https?:)?\/\/[^\s"'<>\\]+?\.(?:mp4|m3u8)(?:\?[^\s"'<>\\]*)?/gi;
const EXT_KIND_RE = /\.(mp4|m3u8)(?:$|\?|#)/i;

export interface ScanOptions {
  pageUrl?: string;
  platform?: Platform;
}

export function scanPageMedia(options: ScanOptions = {}): DetectedMedia[] {
  const pageUrl = options.pageUrl ?? window.location.href;
  const platform = options.platform ?? detectPlatform(pageUrl);
  const found = new Map<string, DetectedMedia>();

  const add = (
    rawUrl: string | null | undefined,
    source: MediaSourceKind,
    mimeType?: string | null,
  ) => {
    const normalized = normalizeUrl(rawUrl, pageUrl);
    if (!normalized || !isCandidateUrl(normalized)) {
      return;
    }
    const kind = resolveKind(normalized, mimeType);
    const id = hashId(normalized);
    const prev = found.get(id);
    if (prev) {
      // Prefer more specific kind / richer mime.
      if (prev.kind === "other" && kind !== "other") {
        prev.kind = kind;
      }
      if (!prev.mimeType && mimeType) {
        prev.mimeType = mimeType;
      }
      return;
    }
    found.set(id, {
      id,
      url: normalized,
      kind,
      source,
      mimeType: mimeType ?? undefined,
      pageUrl,
      platform,
      title: document.title || undefined,
      foundAt: Date.now(),
    });
  };

  document.querySelectorAll("video").forEach((video) => {
    add(video.currentSrc || video.src, "video_tag", video.getAttribute("type"));
    video.querySelectorAll("source").forEach((source) => {
      add(source.src || source.getAttribute("src"), "source_tag", source.type);
    });
  });

  document.querySelectorAll("source").forEach((source) => {
    add(source.src || source.getAttribute("src"), "source_tag", source.type);
  });

  document
    .querySelectorAll<HTMLElement>("[src], [data-src], [href]")
    .forEach((el) => {
      const attrs = ["src", "data-src", "href"] as const;
      for (const attr of attrs) {
        const value = el.getAttribute(attr);
        if (value && looksLikeMediaUrl(value)) {
          add(value, "media_url", el.getAttribute("type"));
        }
      }
    });

  // Visible media URLs in markup / inline scripts (best-effort).
  const htmlSlice = document.documentElement?.innerHTML?.slice(0, 750_000) ?? "";
  for (const match of htmlSlice.matchAll(MEDIA_URL_RE)) {
    add(match[0], "media_url");
  }

  // Network resources already loaded in this document.
  try {
    for (const entry of performance.getEntriesByType("resource")) {
      const name = (entry as PerformanceResourceTiming).name;
      if (looksLikeMediaUrl(name)) {
        add(name, "network");
      }
    }
  } catch {
    // ignore
  }

  return [...found.values()].sort((a, b) => b.foundAt - a.foundAt);
}

export function createMediaWatcher(
  onChange: (items: DetectedMedia[]) => void,
): () => void {
  let timer: number | undefined;
  let lastSignature = "";

  const emit = () => {
    const items = scanPageMedia();
    const signature = items.map((item) => item.id).sort().join("|");
    if (signature === lastSignature) {
      return;
    }
    lastSignature = signature;
    onChange(items);
  };

  const schedule = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(emit, 250);
  };

  const observer = new MutationObserver(schedule);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["src", "href", "data-src", "type"],
  });

  let perfObserver: PerformanceObserver | null = null;
  try {
    perfObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (looksLikeMediaUrl(entry.name)) {
          schedule();
          break;
        }
      }
    });
    perfObserver.observe({ entryTypes: ["resource"] });
  } catch {
    perfObserver = null;
  }

  // Initial + delayed scans for lazy players.
  emit();
  const delays = [800, 2000, 5000];
  const timeoutIds = delays.map((ms) => window.setTimeout(emit, ms));

  return () => {
    observer.disconnect();
    perfObserver?.disconnect();
    window.clearTimeout(timer);
    timeoutIds.forEach((id) => window.clearTimeout(id));
  };
}

export function resolveKind(url: string, mimeType?: string | null): MediaKind {
  const mime = (mimeType ?? "").toLowerCase();
  if (mime.includes("mpegurl") || mime.includes("m3u8")) {
    return "m3u8";
  }
  if (mime.includes("mp4") || mime.includes("video/")) {
    return mime.includes("mp4") ? "mp4" : "video";
  }
  const match = url.match(EXT_KIND_RE);
  if (match?.[1]?.toLowerCase() === "m3u8") {
    return "m3u8";
  }
  if (match?.[1]?.toLowerCase() === "mp4") {
    return "mp4";
  }
  if (url.startsWith("blob:") || url.startsWith("mediasource:")) {
    return "video";
  }
  return "other";
}

function looksLikeMediaUrl(value: string): boolean {
  const lower = value.toLowerCase();
  if (lower.includes(".m3u8") || lower.includes(".mp4")) {
    return true;
  }
  if (lower.startsWith("blob:") || lower.startsWith("mediasource:")) {
    return true;
  }
  return /\/video\/|\/videos\/|mime_type=video|format=mp4|playlist\.m3u8/i.test(
    value,
  );
}

function isCandidateUrl(url: string): boolean {
  if (!url || url.length < 4) {
    return false;
  }
  if (url.startsWith("javascript:") || url.startsWith("data:text")) {
    return false;
  }
  // Keep blob/mediasource from <video>, and http(s) media URLs.
  if (
    url.startsWith("blob:") ||
    url.startsWith("mediasource:") ||
    url.startsWith("http://") ||
    url.startsWith("https://")
  ) {
    return looksLikeMediaUrl(url) || url.startsWith("blob:") || url.startsWith("mediasource:");
  }
  return false;
}

function normalizeUrl(raw: string | null | undefined, pageUrl: string): string | null {
  if (!raw) {
    return null;
  }
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  try {
    if (trimmed.startsWith("//")) {
      return new URL(`${new URL(pageUrl).protocol}${trimmed}`).href;
    }
    return new URL(trimmed, pageUrl).href;
  } catch {
    return null;
  }
}

function hashId(url: string): string {
  let hash = 0;
  for (let i = 0; i < url.length; i += 1) {
    hash = (hash * 31 + url.charCodeAt(i)) >>> 0;
  }
  return `m_${hash.toString(16)}`;
}
