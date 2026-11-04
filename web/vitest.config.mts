import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const fromHere = (path: string) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@/": fromHere("./"),
      // server-only throws on import outside a React server build, so tests load its empty file, as that build does.
      "server-only": fromHere("./node_modules/server-only/empty.js"),
    },
  },
  test: {
    environment: "node",
    include: ["lib/**/*.test.ts"],
  },
});
