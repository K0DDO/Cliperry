import type { AnalyzeResult, AsyncState, FormatInfo } from "../../api";
import type { DetectedMedia, Platform } from "../../shared/types";
import { SUPPORTED_PLATFORMS } from "../../shared/types";
import { StatusBanner } from "../components/StatusBanner";
import { VideoCard } from "../components/VideoCard";
import { platformLabel, shortUrl } from "../lib/labels";

interface Props {
  url: string;
  platform: Platform;
  quality: string;
  mediaCount: number;
  scanning: boolean;
  busy: boolean;
  analyzeState: AsyncState<AnalyzeResult>;
  downloadMessage?: string | null;
  downloadTone?: "loading" | "error" | "success" | null;
  analyzed: AnalyzeResult | null;
  formats: FormatInfo[];
  media: DetectedMedia[];
  onUrlChange: (url: string) => void;
  onAnalyze: () => void;
  onRescan: () => void;
  onQualityChange: (quality: string) => void;
  onDownload: () => void;
  onPickMedia: (item: DetectedMedia) => void;
}

export function MainScreen({
  url,
  platform,
  quality,
  mediaCount,
  scanning,
  busy,
  analyzeState,
  downloadMessage,
  downloadTone,
  analyzed,
  formats,
  media,
  onUrlChange,
  onAnalyze,
  onRescan,
  onQualityChange,
  onDownload,
  onPickMedia,
}: Props) {
  return (
    <div className="screen screen--main">
      <header className="hero">
        <div className="hero__orb hero__orb--berry" aria-hidden="true" />
        <div className="hero__orb hero__orb--sage" aria-hidden="true" />
        <p className="brand">
          <span className="brand__mark" aria-hidden="true">
            🍓
          </span>
          <span className="brand__name">Cliperry</span>
        </p>
        <p className="hero__lead">Premium video downloader for the modern web.</p>
      </header>

      <section className="glass panel">
        <label className="field">
          <span className="field__label">Video link</span>
          <input
            className="field__input"
            type="url"
            value={url}
            placeholder="Paste a YouTube link…"
            spellCheck={false}
            disabled={busy}
            onChange={(event) => onUrlChange(event.target.value)}
          />
        </label>

        <div className="meta-row">
          <span className="chip">{platformLabel(platform)}</span>
          <span className="chip chip--sand">Quality · {quality}</span>
          <span className="chip chip--sage">
            Detected · {mediaCount}
            {scanning ? "…" : ""}
          </span>
        </div>

        <div className="action-row">
          <button
            type="button"
            className="btn btn--berry btn--block"
            disabled={busy || !url.trim()}
            onClick={onAnalyze}
          >
            {analyzeState.status === "loading" ? "Analyzing…" : "Analyze"}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={busy || scanning}
            onClick={onRescan}
          >
            {scanning ? "Scanning…" : "Scan tab"}
          </button>
        </div>
      </section>

      {analyzeState.status === "loading" && (
        <StatusBanner tone="loading">Fetching metadata…</StatusBanner>
      )}
      {analyzeState.status === "error" && (
        <StatusBanner tone="error">{analyzeState.message}</StatusBanner>
      )}
      {downloadTone && downloadMessage ? (
        <StatusBanner tone={downloadTone}>{downloadMessage}</StatusBanner>
      ) : null}

      {analyzed && (
        <VideoCard
          thumbnail={analyzed.thumbnail}
          title={analyzed.title}
          platform={analyzed.platform}
          quality={quality}
          formats={formats}
          author={analyzed.author}
          duration={analyzed.duration}
          downloading={busy && analyzeState.status !== "loading"}
          onQualityChange={onQualityChange}
          onDownload={onDownload}
        />
      )}

      <section className="glass panel panel--soft">
        <div className="section-head">
          <h3>On this page</h3>
          <span>{media.length}</span>
        </div>
        {media.length === 0 ? (
          <p className="empty">No media yet. Open a video and scan the tab.</p>
        ) : (
          <ul className="detect-list">
            {media.slice(0, 5).map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="detect-item"
                  disabled={busy}
                  onClick={() => onPickMedia(item)}
                >
                  <span className={`kind kind--${item.kind}`}>{item.kind}</span>
                  <span className="detect-item__url">{shortUrl(item.url)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="platform-strip" aria-label="Supported platforms">
        {SUPPORTED_PLATFORMS.map((item) => (
          <span key={item.id} className="platform-pill">
            {item.label}
          </span>
        ))}
      </section>
    </div>
  );
}
