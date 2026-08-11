/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * TradeVision backend origin. Defaults to http://localhost:8000 when unset,
   * which is where docker-compose publishes the dev backend.
   */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
