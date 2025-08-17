import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

export default defineConfig({
    build: {
        lib: {
            entry: "src/index.ts",
            formats: ["es"],
            fileName: "index",
        },
        outDir: "dist",
        rollupOptions: {
            external: ["cloudflare:workers"],
        },
        minify: true,
        sourcemap: false,
        target: "esnext",
    },
    resolve: {
        conditions: ["worker", "browser"],
    },
    define: {
        global: "globalThis",
    },
    plugins: [
        {
            name: "graphql-string-loader",
            transform(_code, id) {
                if (id.endsWith(".graphql") || id.endsWith(".gql")) {
                    const graphqlContent = readFileSync(id, "utf-8");
                    return `export default ${JSON.stringify(graphqlContent)}`;
                }
            },
        },
    ],
});
