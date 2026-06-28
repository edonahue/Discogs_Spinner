import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test/setup.ts"],
    // Only collect vitest unit tests (*.test.*). Playwright e2e specs use the
    // *.spec.* suffix under e2e/ and are run separately by `npm run test:e2e`.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
