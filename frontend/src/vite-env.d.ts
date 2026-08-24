/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend base URL. Defaults to http://localhost:8000 if unset. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
