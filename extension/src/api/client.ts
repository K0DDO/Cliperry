/**
 * Cliperry backend HTTP client for the Chrome extension.
 */

import { getApiBaseUrl, getOrCreateDeviceId } from "../shared/storage";
import { ApiError } from "./errors";
import type {
  AnalyzeResult,
  CreateDownloadInput,
  DownloadCreateResult,
  FormatInfo,
  HistoryResult,
  TaskStatusResult,
} from "./types";

const CLIENT_TYPE = "chrome_extension";

export class BackendClient {
  constructor(private readonly baseUrl?: string) {}

  async analyzeUrl(url: string): Promise<AnalyzeResult> {
    return this.request<AnalyzeResult>("/api/analyze", {
      method: "POST",
      body: { url: url.trim() },
    });
  }

  /**
   * Resolve available formats for a URL.
   * Uses analyze endpoint (backend has no separate /formats route).
   */
  async getFormats(url: string): Promise<FormatInfo[]> {
    const result = await this.analyzeUrl(url);
    return result.formats ?? [];
  }

  async createDownload(input: CreateDownloadInput): Promise<DownloadCreateResult> {
    const payload = {
      url: input.url.trim(),
      quality: input.quality.trim(),
      format: input.format ?? "mp4",
      ...(input.title ? { title: input.title } : {}),
      ...(input.platform ? { platform: input.platform } : {}),
    };
    return this.request<DownloadCreateResult>("/api/download", {
      method: "POST",
      body: payload,
    });
  }

  async getTask(taskId: string): Promise<TaskStatusResult> {
    return this.request<TaskStatusResult>(`/api/tasks/${taskId}`, {
      method: "GET",
    });
  }

  async getHistory(page = 1, pageSize = 10): Promise<HistoryResult> {
    return this.request<HistoryResult>(
      `/api/history?page=${page}&page_size=${pageSize}`,
      { method: "GET" },
    );
  }

  private async request<T>(
    path: string,
    options: { method: "GET" | "POST"; body?: unknown },
  ): Promise<T> {
    const baseUrl = (this.baseUrl ?? (await getApiBaseUrl())).replace(/\/$/, "");
    const deviceId = await getOrCreateDeviceId();
    const headers: Record<string, string> = {
      Accept: "application/json",
      "X-Device-Id": deviceId,
      "X-Client-Type": CLIENT_TYPE,
    };

    const init: RequestInit = {
      method: options.method,
      headers,
    };

    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }

    let response: Response;
    try {
      response = await fetch(`${baseUrl}${path}`, init);
    } catch {
      throw new ApiError(
        "Не удалось связаться с сервером Cliperry. Проверьте, что backend запущен.",
        { statusCode: 0, code: "NETWORK" },
      );
    }

    // Persist server-assigned device id if rotated.
    const returnedDevice = response.headers.get("X-Device-Id");
    if (returnedDevice && returnedDevice !== deviceId) {
      const { STORAGE_KEYS } = await import("../shared/types");
      await chrome.storage.local.set({ [STORAGE_KEYS.deviceId]: returnedDevice });
    }

    const payload = await parseBody(response);

    if (!response.ok) {
      throw new ApiError(extractMessage(payload, response.status), {
        statusCode: response.status,
        code: extractCode(payload),
        payload,
      });
    }

    return payload as T;
  }
}

export const api = new BackendClient();

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { message: text };
  }
}

function extractMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object") {
    const data = payload as Record<string, unknown>;
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message;
    }
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    if (Array.isArray(data.detail) && data.detail[0]) {
      const first = data.detail[0] as { msg?: string };
      if (typeof first.msg === "string") {
        return first.msg;
      }
    }
  }
  if (status === 429) {
    return "Слишком много запросов. Подождите немного.";
  }
  if (status === 501) {
    return "Парсер этой платформы ещё не готов.";
  }
  if (status >= 500) {
    return "Сервер Cliperry временно недоступен.";
  }
  return `Ошибка API (${status})`;
}

function extractCode(payload: unknown): string | undefined {
  if (payload && typeof payload === "object") {
    const code = (payload as Record<string, unknown>).code;
    if (typeof code === "string") {
      return code;
    }
  }
  return undefined;
}
