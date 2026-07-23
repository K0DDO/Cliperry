/**
 * Typed event protocol between content ↔ background ↔ popup.
 */

import type { DetectedMedia, Platform, TabMediaState } from "./types";

export type CliperryEvent =
  | { type: "PING"; from?: "popup" | "content" | "background" }
  | { type: "PONG"; source: "background" | "content" }
  | { type: "GET_PAGE_URL" }
  | { type: "PAGE_URL"; url: string; platform: Platform }
  | { type: "REQUEST_SCAN" }
  | { type: "SCAN_NOW" }
  | {
      type: "MEDIA_FOUND";
      pageUrl: string;
      platform: Platform;
      items: DetectedMedia[];
      /** true = replace snapshot for this page; false = merge deltas */
      replace?: boolean;
    }
  | { type: "GET_MEDIA"; tabId?: number }
  | { type: "MEDIA_STATE"; state: TabMediaState | null }
  | { type: "MEDIA_UPDATED"; state: TabMediaState }
  | { type: "ERROR"; message: string; code?: string };

export type CliperryEventType = CliperryEvent["type"];

export function isCliperryEvent(value: unknown): value is CliperryEvent {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    typeof (value as { type: unknown }).type === "string"
  );
}
