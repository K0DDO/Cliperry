import type { HistoryItem } from "../../api";
import { formatDate, platformLabel, statusLabel } from "../lib/labels";

interface Props {
  item: HistoryItem;
}

export function HistoryCard({ item }: Props) {
  return (
    <article className={`history-card glass status-tone--${item.status}`}>
      <div className="history-card__top">
        <h3 className="history-card__title">{item.title || "Без названия"}</h3>
        <span className={`pill pill--${item.status}`}>{statusLabel(item.status)}</span>
      </div>
      <div className="history-card__meta">
        <span>{platformLabel(item.platform)}</span>
        <span>{item.quality || "—"}</span>
        <span>{formatDate(item.created_at)}</span>
      </div>
    </article>
  );
}
