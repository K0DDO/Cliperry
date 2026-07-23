import { defineManifest } from "@crxjs/vite-plugin";
import packageJson from "./package.json";

const { version } = packageJson;

export default defineManifest({
  manifest_version: 3,
  name: "Cliperry",
  version,
  description:
    "Универсальный загрузчик видео — YouTube, TikTok, Instagram, Twitter/X.",
  icons: {
    "16": "icons/icon-16.png",
    "48": "icons/icon-48.png",
    "128": "icons/icon-128.png",
  },
  action: {
    default_popup: "src/popup/index.html",
    default_title: "Cliperry",
    default_icon: {
      "16": "icons/icon-16.png",
      "48": "icons/icon-48.png",
      "128": "icons/icon-128.png",
    },
  },
  background: {
    service_worker: "src/background/service-worker.ts",
    type: "module",
  },
  content_scripts: [
    {
      matches: [
        "*://*.youtube.com/*",
        "*://youtu.be/*",
        "*://*.tiktok.com/*",
        "*://*.instagram.com/*",
        "*://*.twitter.com/*",
        "*://*.x.com/*",
      ],
      js: ["src/content/content.ts"],
      css: ["src/content/content.css"],
      run_at: "document_idle",
    },
  ],
  permissions: ["storage", "activeTab", "scripting", "webRequest"],
  host_permissions: [
    "http://localhost:8000/*",
    "http://127.0.0.1:8000/*",
    "<all_urls>",
  ],
});
