# Cliperry Chrome Extension

Manifest V3 · TypeScript · React · Vite (`@crxjs/vite-plugin`)

## Структура

```
extension/
├── manifest.config.ts      # Manifest V3
├── vite.config.ts
├── src/
│   ├── popup/              # React popup UI
│   ├── background/         # Service worker
│   ├── content/            # Content scripts (YouTube/TikTok/IG/X)
│   └── shared/             # types, storage, platform helpers
└── public/icons/
```

## Разработка

```bash
cd extension
npm install
npm run dev
```

В Chrome: `chrome://extensions` → Developer mode → **Load unpacked** → папка `extension/dist` (CRXJS пишет туда и при `dev`).

## Сборка

```bash
npm run build
```

Загрузить `extension/dist` как unpacked extension.

## Сейчас

- API client: `analyzeUrl()`, `getFormats()`, `createDownload()`
- Popup: состояния loading / error / success для analyze и download
- Детектор страницы + шина событий content ↔ background ↔ popup
