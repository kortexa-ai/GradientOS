/// <reference types="vite/client" />

declare module "occt-import-js" {
  type OcctModule = {
    ReadStepFile: (
      content: Uint8Array,
      params?: Record<string, unknown> | null,
    ) => unknown;
  };

  export default function initOcctImportJs(
    options?: Record<string, unknown>,
  ): Promise<OcctModule>;
}
