# Icon family (Synth app icons)

One visual family for every app, tool and web UI in the fleet. It is the family already shipped by the
Synth forks of Zed and Warp (`synthet/zed` `assets/ICONS.md`, masters in
`assets/branding/jetbrains-darcula-concepts/`). Templates, tokens, project masters and the renderer live in
this skill's `templates/` and `scripts/` (canonical copy: synthet/image-scoring-ui `icons/`).

## Rules

| Element | Rule |
|---|---|
| Canvas | 1024 x 1024 vector master |
| Plate | flat `#101014` rounded square: x/y 64, size 896, radius 184. No gradient, rim, bevel or shadow |
| Surround | transparent outside the plate at every size (no black frame on the Windows desktop) |
| Mark | one idea in silver: gradient `#F8FAFC` to `#C3CFDC` to `#A9B7C6` (x2 0.65, y2 1) on the master, flat `#A9B7C6` on small masters |
| Safe box | mark inside x/y 224..800 |
| Distinctness | every mark is recognisable in grayscale; colour is never the differentiator |
| Variants | release channels share plate and mark; only the glyph tint differs (preview `#6897BB`, nightly `#9876AA`, dev `#CC7832`) |
| Small sizes | hand-simplified `mark-32.svg` (bars >= 96 units, 32-unit grid) and `mark-16.svg` (bars >= 128 units, 64-unit grid) |
| Rendering | rasterise each size directly from the vector (never downscale from 1024) |
| Third-party marks | never copy or imitate another product's logo; draw the project's own idea |

## Fleet marks

| App | Project | Mark | Masters |
|---|---|---|---|
| Vexlum Scoring | image-scoring hub and pipeline | bold V | [`icons/projects/vexlum-scoring`](https://github.com/synthet/image-scoring-ui/tree/main/icons/projects/vexlum-scoring) |
| Driftara Gallery | image-scoring-gallery | Driftara D with a 2x2 photo grid | [`icons/projects/driftara-gallery`](https://github.com/synthet/image-scoring-ui/tree/main/icons/projects/driftara-gallery) |
| Driftara Video | video-gallery | Driftara D with a play mark | [`icons/projects/driftara-video`](https://github.com/synthet/image-scoring-ui/tree/main/icons/projects/driftara-video) |
| AI Quotas | ai-quotas | 270° gauge ring with a centre dot | [`icons/projects/ai-quotas`](https://github.com/synthet/image-scoring-ui/tree/main/icons/projects/ai-quotas) |
| Kestrel | kestrel (desktop review app) | bold K with a raised-wing upper arm | [`icons/projects/kestrel`](https://github.com/synthet/image-scoring-ui/tree/main/icons/projects/kestrel) |
| Zed, Warp | synthet/zed, synthet/warp | labyrinth Z, two-panel mark | in those forks (reference implementation) |

Sub-brands share a base shape and differ by an inner glyph (Driftara: the D).

## Outputs and where they go

`python scripts/render_icons.py --masters <dir> --out <dir>` writes, and verifies:

| File | Use |
|---|---|
| `app.ico` (16-128 BMP32 + 256 PNG) | Windows shortcuts, Electron `icon` on Windows, installers |
| `favicon.ico` (16/32/48) | `<link rel="icon">`, Gradio `favicon_path`, FastAPI static favicon |
| `favicon.svg` (32 px master) | `<link rel="icon" type="image/svg+xml">` |
| `apple-touch-icon.png` (180) | `<link rel="apple-touch-icon">` |
| `icon-192.png`, `icon-512.png` | web manifest `icons` |
| `png/<size>.png` (16-1024) | Electron Linux/macOS icon sources, Expo `icon` (1024), README headers, About windows |

Wiring by surface:

- **Web / Vite / Electron renderer:** copy `favicon.ico`, `favicon.svg`, `apple-touch-icon.png` into the public folder
  and reference them from `index.html`.
- **Gradio / FastAPI:** pass `favicon_path` to `launch()` or serve `favicon.ico` from the static route.
- **Electron main:** `new BrowserWindow({ icon })` with `app.ico` on Windows and `png/512.png` elsewhere; point the
  builder config (`win.icon`, `mac.icon`, `linux.icon`) at the same files.
- **Expo:** `expo.icon` = `png/1024.png`; Android adaptive foreground = the mark on transparent at 1024 with
  `backgroundColor` `#101014`.
- **Windows desktop shortcuts:** `IconLocation` = an installed copy of `app.ico` outside any git checkout (for
  example `%LOCALAPPDATA%\SynthIcons\<project>.ico`), so branch switches cannot remove it.

## Checks

`scripts/render_icons.py --check <out>` probes all four corners and edge midpoints of every PNG and ICO frame for the
transparent surround, confirms the ICO frame sizes, and that sub-256 frames are BMP32 and the 256 frame is PNG.
