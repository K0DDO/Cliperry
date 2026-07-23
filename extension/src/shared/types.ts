/** Shared domain types for Cliperry extension. */

export type Platform =
  | "youtube"
  | "tiktok"
  | "instagram"
  | "twitter"
  | "unknown";

export type MediaKind = "mp4" | "m3u8" | "video" | "other";

export type MediaSourceKind =
  | "video_tag"
  | "source_tag"
  | "media_url"
  | "network";

export interface DetectedMedia {
  id: string;
  url: string;
  kind: MediaKind;
  source: MediaSourceKind;
  mimeType?: string;
  pageUrl: string;
  platform: Platform;
  title?: string;
  foundAt: number;
}

export interface TabMediaState {
  tabId: number;
  pageUrl: string;
  platform: Platform;
  items: DetectedMedia[];
  updatedAt: number;
}

export const STORAGE_KEYS = {
  deviceId: "cliperry_device_id",
  apiBaseUrl: "cliperry_api_base_url",
  defaultQuality: "cliperry_default_quality",
  mediaByTab: "cliperry_media_by_tab",
} as const;

export const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/** Platforms fully supported for download today. */
export const READY_PLATFORMS = [{ id: "youtube", label: "YouTube", hostHint: "youtube.com" }] as const;

export const SUPPORTED_PLATFORMS = [
  ...READY_PLATFORMS,
  { id: "tiktok", label: "TikTok (soon)", hostHint: "tiktok.com" },
  { id: "instagram", label: "Instagram (soon)", hostHint: "instagram.com" },
  { id: "twitter", label: "Twitter / X (soon)", hostHint: "x.com" },
] as const;
