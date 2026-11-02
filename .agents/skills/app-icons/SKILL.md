---
name: app-icons
description: "Use when creating, redesigning or applying an app icon, favicon, Windows .ico, Electron/Expo icon, PWA/touch icon or desktop-shortcut icon for a project, or when the user asks for icons in the Zed/Warp (Synth) style. Designs the project's mark on the shared Synth plate, renders every size from vector masters, verifies them, and wires them into the project's surfaces."
capability: "Design, render, verify and wire Synth-family app icons and favicons"
side_effect_level: local_write
approval_required: false
requires_tools: "Python 3 with Pillow (uv run --with pillow), ImageMagick 7 `magick` with SVG support; git"
output_schema: "Masters (mark.svg, mark-32.svg, mark-16.svg), rendered icon set, per-surface wiring diff, check output"
risk_class: low
---

# App icons (Synth family)

Every app, tool and web UI shares one icon family: a flat `#101014` rounded plate, one silver mark, a
transparent surround. It is the family shipped by the Synth Zed and Warp forks. Rules, sizes and wiring are in
[`references/family-spec.md`](references/family-spec.md). Read it before drawing.

## 1. Design the mark

1. Copy `templates/mark-1024.svg` to `<project>/assets/icons/mark.svg`, and `templates/mark-32.svg` and
   `templates/mark-16.svg` next to it.
2. Draw **one idea** for the project inside the safe box (x/y 224..800) as filled paths in the `glyph` group:
   a letter, a simple object or a geometric metaphor. Two or three shapes at most.
3. It must stay distinct **in grayscale** from the other fleet marks listed in the spec (V, Driftara D, gauge ring,
   K, labyrinth Z, two-panel Warp). Sub-brands keep the shared base shape and change only an inner glyph.
4. Never copy or imitate another product's logo, and never use a third party's trademark as the mark.
5. Simplify by hand for small sizes: `mark-32.svg` with bars of at least 96 units on a 32-unit grid,
   `mark-16.svg` with bars of at least 128 units on a 64-unit grid. Drop inner detail that would blur.

## 2. Render and verify

```
uv run --with pillow python <skill-dir>/scripts/render_icons.py --masters <project>/assets/icons --out <project>/assets/icons/out
```

This writes the PNG sizes 16-1024, `favicon.ico`, `app.ico` (BMP32 below 256 px plus PNG at 256), `favicon.svg`,
`apple-touch-icon.png` and `icon-192.png`/`icon-512.png`, then checks the transparent surround and ICO
encodings. Re-check later with `--check <out>`. Add `--tint #RRGGBB` only for release channels.

Look at the result before wiring it: build a contact sheet of 256, 48, 32 and 16 px on a light background and
view it. If the 16 px version reads as noise, simplify `mark-16.svg` further.

## 3. Wire the surfaces

Wire only the surfaces the project has (details in the spec):

| Surface | Files |
|---|---|
| Web / Vite / Electron renderer | `favicon.ico`, `favicon.svg`, `apple-touch-icon.png` in the public folder, linked from `index.html` |
| Gradio / FastAPI | `favicon.ico` via `favicon_path` or the static route |
| Electron main and builder | `app.ico` (Windows) and `png/512.png` (macOS/Linux) |
| Expo | add `--expo`: `expo/icon.png` as `icon`, `adaptive-foreground.png` and `monochrome.png` for the adaptive icon (background `#101014`), `splash-icon.png`, `favicon.png` |
| Web manifest | `icon-192.png`, `icon-512.png` |
| Windows desktop shortcut | an installed copy of `app.ico` outside the checkout, e.g. `%LOCALAPPDATA%\SynthIcons\<project>.ico` |

Keep the masters in git, and treat rendered files as build outputs unless a surface needs them committed (for
example a web public folder).

## 4. Before you finish

- `--check` passes on the output folder.
- The contact sheet was viewed, and the mark is legible at 16 px.
- Shortcuts and app manifests point at the new files; old icon files are removed only if nothing references them.
- The change goes through the project's normal branch and PR workflow.

The canonical copies of the templates, tokens and renderer live in `synthet/image-scoring-ui` (`icons/`). The
copies here record their source commit; update them together.
