import { useCallback, useEffect, useState } from "react";
import { api, toUserMessage, type AsyncState, type HistoryResult } from "../../api";
import { HistoryCard } from "../components/HistoryCard";
import { StatusBanner } from "../components/StatusBanner";

export function HistoryScreen() {
  const [page, setPage] = useState(1);
  const [state, setState] = useState<AsyncState<HistoryResult>>({ status: "idle" });

  const load = useCallback(async (nextPage: number) => {
    setState({ status: "loading", message: "Loading history…" });
    try {
      const data = await api.getHistory(nextPage, 10);
      setState({ status: "success", data });
      setPage(data.page);
    } catch (error) {
      setState({ status: "error", message: toUserMessage(error) });
    }
  }, []);

  useEffect(() => {
    void load(1);
  }, [load]);

  const data = state.status === "success" ? state.data : null;

  return (
    <div className="screen screen--history">
      <header className="screen-header">
        <p className="eyebrow">Library</p>
        <h1 className="screen-title">History</h1>
        <p className="screen-lead">Last downloads from this device.</p>
      </header>

      {state.status === "loading" && (
        <StatusBanner tone="loading">Loading history…</StatusBanner>
      )}
      {state.status === "error" && (
        <StatusBanner tone="error">{state.message}</StatusBanner>
      )}

      {data && data.items.length === 0 && (
        <div className="glass panel empty-panel">
          <span className="empty-panel__mark" aria-hidden="true">
            🍓
          </span>
          <p>No downloads yet. Analyze a link on Main to begin.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="history-list">
            {data.items.map((item) => (
              <HistoryCard key={item.id} item={item} />
            ))}
          </div>

          <div className="pager">
            <button
              type="button"
              className="btn btn--ghost"
              disabled={!data.has_prev || state.status === "loading"}
              onClick={() => void load(page - 1)}
            >
              Prev
            </button>
            <span className="pager__label">
              {data.page} / {Math.max(data.total_pages, 1)}
            </span>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={!data.has_next || state.status === "loading"}
              onClick={() => void load(page + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
