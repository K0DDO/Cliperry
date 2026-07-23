import { useCallback, useEffect, useState } from "react";
import {
  api,
  toUserMessage,
  type AnalyzeResult,
  type AsyncState,
  type DownloadCreateResult,
  type FormatInfo,
} from "../api";
import { onEvent, requestEvent } from "../shared/messaging";
import { detectPlatform, isSupportedUrl } from "../shared/platform";
import { getDefaultQuality } from "../shared/storage";
import type { DetectedMedia, Platform, TabMediaState } from "../shared/types";
import { BottomNav } from "./components/BottomNav";
import type { ScreenId } from "./lib/labels";
import { normalizePlatform } from "./lib/labels";
import { HistoryScreen } from "./screens/HistoryScreen";
import { MainScreen } from "./screens/MainScreen";
import { SettingsScreen } from "./screens/SettingsScreen";

export function App() {
  const [screen, setScreen] = useState<ScreenId>("main");
  const [url, setUrl] = useState("");
  const [platform, setPlatform] = useState<Platform>("unknown");
  const [quality, setQuality] = useState("720p");
  const [media, setMedia] = useState<DetectedMedia[]>([]);
  const [scanning, setScanning] = useState(false);

  const [analyzeState, setAnalyzeState] = useState<AsyncState<AnalyzeResult>>({
    status: "idle",
  });
  const [downloadState, setDownloadState] = useState<
    AsyncState<DownloadCreateResult>
  >({ status: "idle" });

  const analyzed = analyzeState.status === "success" ? analyzeState.data : null;
  const formats = analyzed?.formats ?? [];
  const busy =
    analyzeState.status === "loading" || downloadState.status === "loading";

  const applyMediaState = useCallback((state: TabMediaState | null) => {
    if (!state) {
      setMedia([]);
      return;
    }
    setMedia(state.items);
    if (state.pageUrl) {
      setUrl((prev) => prev || state.pageUrl);
      setPlatform(state.platform);
    }
  }, []);

  useEffect(() => {
    void bootstrap();
    const stop = onEvent((event) => {
      if (event.type === "MEDIA_UPDATED") {
        applyMediaState(event.state);
      }
    });
    return stop;
  }, [applyMediaState]);

  async function bootstrap() {
    setQuality(await getDefaultQuality());
    try {
      const page = await requestEvent({ type: "GET_PAGE_URL" }, "PAGE_URL");
      if (page?.url) {
        applyUrl(page.url, page.platform);
      }
      const mediaResponse = await requestEvent({ type: "GET_MEDIA" }, "MEDIA_STATE");
      if (mediaResponse) {
        applyMediaState(mediaResponse.state);
      }
      setScanning(true);
      const scanned = await requestEvent({ type: "REQUEST_SCAN" }, "MEDIA_STATE");
      if (scanned) {
        applyMediaState(scanned.state);
      }
    } finally {
      setScanning(false);
    }
  }

  function applyUrl(nextUrl: string, nextPlatform?: Platform) {
    setUrl(nextUrl);
    setAnalyzeState({ status: "idle" });
    setDownloadState({ status: "idle" });
    setPlatform(nextPlatform ?? detectPlatform(nextUrl));
  }

  async function onRescan() {
    setScanning(true);
    try {
      const scanned = await requestEvent({ type: "REQUEST_SCAN" }, "MEDIA_STATE");
      if (scanned) {
        applyMediaState(scanned.state);
      }
    } finally {
      setScanning(false);
    }
  }

  async function onAnalyze() {
    if (!url.trim()) {
      setAnalyzeState({ status: "error", message: "Paste a video link first." });
      return;
    }
    if (!isSupportedUrl(url)) {
      setAnalyzeState({
        status: "error",
        message: "This link is not supported by Cliperry yet.",
      });
      return;
    }

    setDownloadState({ status: "idle" });
    setAnalyzeState({ status: "loading", message: "Analyzing…" });

    try {
      const result = await api.analyzeUrl(url);
      const formatList: FormatInfo[] =
        result.formats?.length > 0 ? result.formats : await api.getFormats(url);
      const merged: AnalyzeResult = { ...result, formats: formatList };
      setAnalyzeState({ status: "success", data: merged });
      setPlatform(normalizePlatform(merged.platform));
      const preferred = pickPreferredQuality(formatList, quality);
      if (preferred) {
        setQuality(preferred);
      }
    } catch (error) {
      setAnalyzeState({ status: "error", message: toUserMessage(error) });
    }
  }

  async function onDownload() {
    if (!analyzed) {
      return;
    }
    const selected =
      formats.find((item) => item.quality === quality) ?? formats[0];
    if (!selected) {
      setDownloadState({ status: "error", message: "No formats available." });
      return;
    }

    setDownloadState({
      status: "loading",
      message: `Creating download · ${selected.quality}`,
    });

    try {
      const created = await api.createDownload({
        url: analyzed.url || url,
        quality: selected.quality,
        format: selected.format || "mp4",
        title: analyzed.title,
        platform: analyzed.platform,
      });
      setDownloadState({
        status: "success",
        data: created,
        message: `Queued · ${created.task_id.slice(0, 8)}`,
      });
    } catch (error) {
      setDownloadState({ status: "error", message: toUserMessage(error) });
    }
  }

  const downloadTone =
    downloadState.status === "loading" ||
    downloadState.status === "error" ||
    downloadState.status === "success"
      ? downloadState.status
      : null;

  return (
    <div className="app">
      <div className="app__glow" aria-hidden="true" />
      <div className="app__content">
        {screen === "main" && (
          <MainScreen
            url={url}
            platform={platform}
            quality={quality}
            mediaCount={media.length}
            scanning={scanning}
            busy={busy}
            analyzeState={analyzeState}
            downloadMessage={
              downloadState.status === "idle" ? null : downloadState.message ?? null
            }
            downloadTone={downloadTone}
            analyzed={analyzed}
            formats={formats}
            media={media}
            onUrlChange={(value) => applyUrl(value)}
            onAnalyze={() => void onAnalyze()}
            onRescan={() => void onRescan()}
            onQualityChange={setQuality}
            onDownload={() => void onDownload()}
            onPickMedia={(item) => applyUrl(item.pageUrl || item.url, item.platform)}
          />
        )}
        {screen === "history" && <HistoryScreen />}
        {screen === "settings" && <SettingsScreen />}
      </div>
      <BottomNav active={screen} onChange={setScreen} />
    </div>
  );
}

function pickPreferredQuality(
  formats: FormatInfo[],
  preferred: string,
): string | null {
  if (!formats.length) {
    return null;
  }
  const exact = formats.find(
    (item) => item.quality.toLowerCase() === preferred.toLowerCase(),
  );
  return exact?.quality ?? formats[0]?.quality ?? null;
}
