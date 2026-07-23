import type { Platform } from "../../shared/types";

export type ScreenId = "main" | "history" | "settings";

export function platformLabel(platform: string): string {
  switch (platform.toLowerCase()) {
    case "youtube":
      return "YouTube";
    case "tiktok":
      return "TikTok";
    case "instagram":
      return "Instagram";
    case "twitter":
      return "Twitter / X";
    default:
      return platform || "Unknown";
  }
}

export function normalizePlatform(value: string): Platform {
  const key = value.toLowerCase();
  if (
    key === "youtube" ||
    key === "tiktok" ||
    key === "instagram" ||
    key === "twitter"
  ) {
    return key;
  }
  return "unknown";
}

export function statusLabel(status: string): string {
  switch (status.toLowerCase()) {
    case "completed":
      return "Готово";
    case "failed":
      return "Ошибка";
    case "processing":
      return "В работе";
    case "queued":
      return "В очереди";
    default:
      return status;
  }
}

export function formatDate(value: string): string {
  try {
    const dt = new Date(value);
    return dt.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function shortUrl(value: string): string {
  try {
    const parsed = new URL(value);
    const path = `${parsed.pathname}${parsed.search}`.slice(0, 40);
    return `${parsed.hostname}${path}${path.length >= 40 ? "…" : ""}`;
  } catch {
    return value.slice(0, 48);
  }
}
