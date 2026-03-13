# ⚛️ Frontend Overview

The frontend is a **Next.js 15** application written in TypeScript. It provides the web UI for creating voices, recording samples, training embeddings, and generating speech.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Directory Structure](#directory-structure)
- [Routing](#routing)
- [State Management Philosophy](#state-management-philosophy)
- [Styling](#styling)
- [Environment Variables](#environment-variables)
- [Development Workflow](#development-workflow)

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 15 | React framework with file-based routing and SSR |
| **React** | 18 | UI component model |
| **TypeScript** | 5 | Type safety across the entire codebase |
| **Tailwind CSS** | 3.3 | Utility-first styling |
| **PostCSS** | — | CSS processing pipeline (required by Tailwind) |
| **MediaRecorder API** | Browser native | Records audio from the microphone in the browser |

> 💡 There is **no Redux, Zustand, or other global state library**. Each page manages its own local state with React `useState` and `useEffect`. This is intentional — the app is simple enough that global state would be overkill.

---

## Directory Structure

```
frontend/
├── app/                            # Next.js App Router
│   ├── layout.tsx                  # Root layout — navigation bar, global styles
│   ├── page.tsx                    # Home / dashboard  (route: /)
│   ├── globals.css                 # Tailwind directives + CSS variables
│   │
│   ├── voices/
│   │   └── page.tsx                # Voice CRUD panel  (route: /voices)
│   │
│   ├── record/
│   │   └── page.tsx                # Guided recording wizard  (route: /record)
│   │
│   ├── generate/
│   │   └── page.tsx                # TTS generation panel  (route: /generate)
│   │
│   └── lib/
│       └── api.ts                  # All backend API calls in one place
│
├── public/                         # Static assets (images, icons, etc.)
├── package.json                    # Dependencies and npm scripts
├── tsconfig.json                   # TypeScript compiler options
├── tailwind.config.js              # Tailwind theme customisation
├── postcss.config.js               # PostCSS plugins
└── next.config.js                  # Next.js configuration
```

---

## Routing

Next.js uses **file-based routing** — the directory structure under `app/` maps directly to URL paths:

| File | URL | Description |
|------|-----|-------------|
| `app/page.tsx` | `/` | Home / dashboard |
| `app/voices/page.tsx` | `/voices` | Voice management |
| `app/record/page.tsx` | `/record` | Recording wizard |
| `app/generate/page.tsx` | `/generate` | TTS generation |

`app/layout.tsx` wraps every page with the navigation bar and common HTML structure (fonts, metadata, etc.).

---

## State Management Philosophy

Each page component follows the same pattern:

```tsx
// Typical page pattern
"use client";                        // Mark as a Client Component (needs browser APIs)

import { useState, useEffect } from "react";
import { api } from "../lib/api";

export default function VoicesPage() {
  // 1. Declare local state
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);

  // 2. Fetch data on mount
  useEffect(() => {
    api.listVoices().then(setVoices).finally(() => setLoading(false));
  }, []);

  // 3. Render
  return (…);
}
```

> ⚠️ Pages are marked `"use client"` because they use browser-only APIs (`MediaRecorder`, `fetch`, `useState`). Server-side rendering is not used — all data is fetched client-side after mount.

---

## Styling

All styling is done with **Tailwind CSS utility classes** applied directly in JSX. There is no separate CSS module or styled-component layer.

Custom theme colours are defined in `tailwind.config.js`:

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {           // Used as "bg-primary-600", "text-primary-700", etc.
          50:  "#…",
          // … 100 through 950
          600: "#…",
        },
      },
    },
  },
};
```

`globals.css` sets up the Tailwind base layers:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000/api/v1` | Base URL for all backend API calls |

The `NEXT_PUBLIC_` prefix is required by Next.js to expose the variable to the browser bundle (as opposed to server-side-only variables).

Set this at build time or in your `.env.local` file:

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1
```

---

## Development Workflow

```bash
cd frontend

# Install dependencies
npm install

# Start development server with hot-reload
npm run dev                   # → http://localhost:3000

# Type-check without building
npx tsc --noEmit

# Build for production
npm run build

# Start production server
npm start
```

> 💡 The development server (`npm run dev`) proxies API requests to the backend automatically if you configure `rewrites` in `next.config.js`, or you can set `NEXT_PUBLIC_API_BASE` to point directly at the backend URL.
