import { useEffect, useState } from "react";
import {
  DEFAULT_API_BASE_URL,
  getApiBaseUrl,
  getDefaultQuality,
  getOrCreateDeviceId,
  setApiBaseUrl,
  setDefaultQuality,
} from "../../shared/storage";
import { StatusBanner } from "../components/StatusBanner";

const QUALITIES = ["1080p", "720p", "480p", "audio"] as const;

export function SettingsScreen() {
  const [quality, setQuality] = useState("720p");
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_BASE_URL);
  const [deviceId, setDeviceId] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setQuality(await getDefaultQuality());
      setApiUrl(await getApiBaseUrl());
      setDeviceId(await getOrCreateDeviceId());
    })();
  }, []);

  async function onSave() {
    setError(null);
    setSaved(false);
    try {
      if (!apiUrl.trim()) {
        throw new Error("API URL is required");
      }
      new URL(apiUrl.trim());
      await setApiBaseUrl(apiUrl);
      await setDefaultQuality(quality);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save settings");
    }
  }

  return (
    <div className="screen screen--settings">
      <header className="screen-header">
        <p className="eyebrow">Preferences</p>
        <h1 className="screen-title">Settings</h1>
        <p className="screen-lead">Tune Cliperry for this browser profile.</p>
      </header>

      <section className="glass panel">
        <label className="field">
          <span className="field__label">Default quality</span>
          <div className="quality-grid">
            {QUALITIES.map((item) => (
              <button
                key={item}
                type="button"
                className={`quality-option ${quality === item ? "quality-option--active" : ""}`}
                onClick={() => setQuality(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </label>

        <label className="field">
          <span className="field__label">Backend URL</span>
          <input
            className="field__input"
            type="url"
            value={apiUrl}
            spellCheck={false}
            onChange={(event) => setApiUrl(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Device ID</span>
          <input className="field__input field__input--mono" value={deviceId} readOnly />
        </label>

        <button type="button" className="btn btn--berry btn--block" onClick={() => void onSave()}>
          Save settings
        </button>
      </section>

      {saved && <StatusBanner tone="success">Settings saved</StatusBanner>}
      {error && <StatusBanner tone="error">{error}</StatusBanner>}

      <section className="glass panel panel--soft">
        <div className="section-head">
          <h3>Palette</h3>
        </div>
        <div className="swatches">
          <span className="swatch swatch--berry" title="Berry Pink" />
          <span className="swatch swatch--rose" title="Soft Rose" />
          <span className="swatch swatch--sand" title="Warm Sand" />
          <span className="swatch swatch--sage" title="Sage" />
          <span className="swatch swatch--ivory" title="Ivory" />
        </div>
      </section>
    </div>
  );
}
