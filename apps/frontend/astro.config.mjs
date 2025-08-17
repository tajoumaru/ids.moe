// @ts-check
import { defineConfig, envField } from 'astro/config';

import cloudflare from '@astrojs/cloudflare';

import tailwindcss from '@tailwindcss/vite';
import clerk from "@clerk/astro";

import react from "@astrojs/react";

// https://astro.build/config
export default defineConfig({
    adapter: cloudflare({
        platformProxy: {
            enabled: true
        },

        imageService: "cloudflare"
    }),

    integrations: [clerk({
        enableEnvSchema: true
    }), react()],

    vite: {
        plugins: [tailwindcss()],
    },

    output: "server",
});
