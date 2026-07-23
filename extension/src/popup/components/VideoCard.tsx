import type { FormatInfo } from "../../api";
import { platformLabel } from "../lib/labels";

interface Props {
  thumbnail?: string | null;
  title: string;
  platform: string;
  quality: string;
  formats: FormatInfo[];
  author?: string | null;
  duration?: string | null;
  downloading?: boolean;
  onQualityChange: (quality: string) => void;
  onDownload: () => void;
}

export function VideoCard({
  thumbnail,
  title,
  platform,
  quality,
  formats,
  author,
  duration,
  downloading = false,
  onQualityChange,
  onDownload,
}: Props) {
  return (
    <article className="video-card glass glass--lift">
      <div className="video-card__media">
        {thumbnail ? (
          <img src={thumbnail} alt="" className="video-card__thumb" loading="lazy" />
        ) : (
          <div className="video-card__thumb video-card__thumb--empty" aria-hidden="true">
            <span>🍓</span>
          </div>
        )}
        <div className="video-card__shade" aria-hidden="true" />
        <span className="video-card__platform">{platformLabel(platform)}</span>
        {duration ? <span className="video-card__duration">{duration}</span> : null}
      </div>

      <div className="video-card__body">
        <h2 className="video-card__title">{title}</h2>
        {author ? <p className="video-card__author">{author}</p> : null}

        <div className="video-card__row">
          <label className="video-card__quality">
            <span className="video-card__quality-label">Quality</span>
            <select
              className="video-card__select"
              value={quality}
              disabled={downloading || formats.length === 0}
              onChange={(event) => onQualityChange(event.target.value)}
            >
              {(formats.length ? formats : [{ quality, format: "mp4" }]).map((fmt) => (
                <option key={`${fmt.quality}-${fmt.format}`} value={fmt.quality}>
                  {fmt.quality}
                  {fmt.size ? ` · ${fmt.size}` : ""}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            className="btn btn--berry"
            disabled={downloading}
            onClick={onDownload}
          >
            {downloading ? "Downloading…" : "Download"}
          </button>
        </div>
      </div>
    </article>
  );
}
