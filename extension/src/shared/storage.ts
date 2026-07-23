import {
  DEFAULT_API_BASE_URL,
  STORAGE_KEYS,
} from "./types";

function randomUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function getOrCreateDeviceId(): Promise<string> {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.deviceId);
  const existing = stored[STORAGE_KEYS.deviceId];
  if (typeof existing === "string" && existing.length > 0) {
    return existing;
  }
  const deviceId = randomUuid();
  await chrome.storage.local.set({ [STORAGE_KEYS.deviceId]: deviceId });
  return deviceId;
}

export async function getApiBaseUrl(): Promise<string> {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.apiBaseUrl);
  const value = stored[STORAGE_KEYS.apiBaseUrl];
  return typeof value === "string" && value.length > 0
    ? value.replace(/\/$/, "")
    : DEFAULT_API_BASE_URL;
}

export async function getDefaultQuality(): Promise<string> {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.defaultQuality);
  const value = stored[STORAGE_KEYS.defaultQuality];
  return typeof value === "string" && value.length > 0 ? value : "720p";
}

export async function setDefaultQuality(quality: string): Promise<void> {
  await chrome.storage.local.set({ [STORAGE_KEYS.defaultQuality]: quality });
}

export async function setApiBaseUrl(url: string): Promise<void> {
  const cleaned = url.trim().replace(/\/$/, "");
  await chrome.storage.local.set({
    [STORAGE_KEYS.apiBaseUrl]: cleaned || DEFAULT_API_BASE_URL,
  });
}
