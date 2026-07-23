/** Backend API DTOs mirrored from Cliperry FastAPI schemas. */

export interface FormatInfo {
  quality: string;
  format: string;
  size?: string | null;
  format_id?: string | null;
  has_audio?: boolean;
  has_video?: boolean;
}

export interface PlaylistEntryInfo {
  id: string;
  title: string;
  thumbnail?: string | null;
  url?: string | null;
  duration?: string | null;
  index?: number | null;
}

export interface AnalyzeResult {
  platform: string;
  title: string;
  thumbnail?: string | null;
  formats: FormatInfo[];
  author?: string | null;
  duration?: string | null;
  url: string;
  is_playlist?: boolean;
  playlist_count?: number | null;
  entries?: PlaylistEntryInfo[];
}

export interface CreateDownloadInput {
  url: string;
  quality: string;
  format?: string;
  title?: string;
  platform?: string;
}

export interface DownloadCreateResult {
  task_id: string;
  status: string;
  download_id: string;
}

export interface TaskStatusResult {
  task_id: string;
  status: string;
  progress: number;
  speed?: string | null;
  eta?: string | null;
  size?: string | null;
  error_message?: string | null;
  download_url?: string | null;
  title?: string | null;
  platform?: string | null;
  quality?: string | null;
}

export interface HistoryItem {
  id: string;
  title?: string | null;
  platform: string;
  status: string;
  quality?: string | null;
  created_at: string;
}

export interface HistoryResult {
  items: HistoryItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

/** Shared async UI state for API calls. */
export type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading"; message?: string }
  | { status: "success"; data: T; message?: string }
  | { status: "error"; message: string };
