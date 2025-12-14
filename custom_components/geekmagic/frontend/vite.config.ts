import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, "src/geekmagic-panel.ts"),
      name: "GeekMagicPanel",
      fileName: () => "geekmagic-panel.js",
      formats: ["es"],
    },
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      // Don't externalize - bundle everything
      external: [],
    },
    minify: true,
    sourcemap: false,
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});
