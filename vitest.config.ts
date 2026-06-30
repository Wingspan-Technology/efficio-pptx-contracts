import { defineConfig } from "vitest/config";

// Per-test timeouts keep the suite from hanging an agent indefinitely.
export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    testTimeout: 5000,
    hookTimeout: 5000,
    teardownTimeout: 5000,
  },
});
