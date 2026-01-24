# ECHO OMEGA PRIME - UNIFIED APPS DIRECTORY

**Authority:** 11.0 SOVEREIGN | **Commander:** Bobby Don McWilliams II

---

## Structure

Every app follows the **Mobile + Web + Desktop** pattern with synced data.

```
APPS/
├── _SHARED/                    # Cross-app shared code
│   ├── components/             # React/Native components
│   ├── hooks/                  # Shared hooks
│   ├── lib/                    # Firebase, API clients
│   ├── types/                  # TypeScript types
│   └── styles/                 # Echo Design System
│
├── closer/                     # CLOSER - AI Sales Assistant
├── gameloop/                   # GameLoop - Gaming AI
├── immortality-vault/          # Immortality Vault - Memory Preservation
├── collectibles-grading/       # Collectibles Grading System
├── echo-clip/                  # Echo Clip - Video Editor
├── echo-coin/                  # $ECHO Cryptocurrency
├── barking-lot/                # Barking Lot - Pet AI
├── shadowglass/                # Shadowglass - Security Tool
└── echo-prime-website/         # echo-op.com Main Website
```

---

## App Template Structure

Each app directory follows this standard:

```
app-name/
├── package.json                # Workspace root (pnpm/npm)
├── README.md                   # App documentation
├── CLAUDE.md                   # App-specific Claude directives
│
├── mobile/                     # React Native + Expo
│   ├── app/                    # Expo Router
│   ├── components/
│   ├── lib/
│   ├── app.json
│   ├── eas.json
│   └── package.json
│
├── web/                        # Next.js 14
│   ├── app/                    # App Router
│   ├── components/
│   ├── lib/
│   ├── public/
│   ├── next.config.js
│   └── package.json
│
├── desktop/                    # Electron
│   ├── main/
│   ├── renderer/
│   ├── electron-builder.yml
│   └── package.json
│
├── api/                        # Backend (optional)
│   ├── src/
│   ├── Dockerfile
│   └── requirements.txt
│
└── shared/                     # App-specific shared
    ├── types/
    ├── constants/
    └── utils/
```

---

## Shared Components (_SHARED/)

Common components used across all apps:

- **Firebase client** - Authentication, Firestore, Storage
- **Echo Design System** - Colors, typography, animations
- **API clients** - GS343, Phoenix, PROMETHEUS, MEGA GATEWAY
- **Type definitions** - Shared TypeScript interfaces

---

## Development Commands

```bash
# Mobile development
cd APPS/closer/mobile
npx expo start

# Web development
cd APPS/closer/web
npm run dev

# Desktop development
cd APPS/closer/desktop
npm run electron:dev

# Build for production
npm run build
```

---

## Syncing Data

All platforms sync via Firebase Firestore in real-time:
- User data: `users/{uid}/`
- App data: `apps/{appId}/users/{uid}/`
- Shared data: `shared/{collection}/`

---

*ECHO OMEGA PRIME | Authority 11.0 | APPS DIRECTORY*
