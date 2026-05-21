# Hermes ZenMux Image Generation Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-≥%200.7.0-blue)](https://github.com/nousresearch/hermes-agent)

English Version | [中文版本](./README.zh-CN.md)

Teach your Hermes AI assistant to draw — one API Key for both OpenAI and Google Gemini image generation models.

---

## 😵‍💫 What Is This?

**In one sentence:** This plugin lets Hermes generate images. You say "draw a cat" and it draws a cat.

Hermes itself is a text-only assistant — it can't draw. This plugin connects it to image generation via the [ZenMux](https://zenmux.ai/invite/1C3QLF) API gateway. One ZenMux API Key gives you access to models from both OpenAI and Google — no need to sign up for each separately.

---

## ✨ Supported Models

| Model | Speed | Best For |
|-------|-------|----------|
| **GPT Image 2** (OpenAI) | ~15-40s | High quality, text-in-image capability |
| **GPT Image 2 High** (OpenAI) | ~40-120s | Maximum fidelity — slow but exquisite |
| **Gemini 3.1 Flash Image** (Google) | ~10-30s | Fast, great for everyday use |

> 📸 `[screenshot]` — Side-by-side comparison of the three models generating the same prompt (e.g., "a calico cat wearing a crown"), so readers can see the style differences at a glance

---

## 🚀 Quick Start (3 Steps)

### Prerequisites

- ✅ Running [Hermes Agent](https://github.com/nousresearch/hermes-agent) (≥ 0.7.0)
- ✅ A [ZenMux](https://zenmux.ai/invite/1C3QLF) account and API Key

---

### Step 1: Install the Plugin

```bash
hermes plugins install colin-chang/hermes-plugin-zenmux-image --enable
```

### Step 2: Configure API Key

Open `~/.hermes/.env` and add:

```bash
ZENMUX_API_KEY=your-zenmux-api-key
```

### Step 3: Set the Image Generation Backend

Add to `~/.hermes/config.yaml`:

```yaml
image_gen:
  provider: zenmux
  zenmux:
    model: openai/gpt-image-2   # default; change to whatever you prefer
```

Restart Hermes to apply. Now try telling Hermes "Draw a cat wearing a crown."

---

## 📖 Usage Guide

### Basic Usage

Just tell Hermes what you want to draw, the same way you'd chat normally:

> Draw a cyberpunk city night scene, neon lights reflecting in rainwater

> Generate a poster: an astronaut cat planting the Chinese flag on the moon, photorealistic style

### Switching Models

**Method 1: Mention it in your prompt** (no config change needed)

- Say "Draw a cat with **Gemini**" → auto-switches to Gemini
- Say "Draw a city with **OpenAI**" → auto-switches to GPT Image 2

**Method 2: Edit the config file**

```yaml
image_gen:
  zenmux:
    model: google/gemini-3.1-flash-image-preview
```

**Method 3: Environment variable**

```bash
export ZENMUX_IMAGE_MODEL=google/gemini-3.1-flash-image-preview
```

### Model Selection Priority

When multiple methods are active simultaneously, priority from highest to lowest:

1. Prompt keyword (e.g., "use Gemini" → auto-selects Gemini)
2. `ZENMUX_IMAGE_MODEL` environment variable
3. `image_gen.zenmux.model` config setting
4. Default model: `openai/gpt-image-2`

---

## 🧱 How Does It Work?

In plain language:

```
You say "draw a cat" ──→ Hermes Gateway ──→ This plugin ──→ ZenMux API ──→ OpenAI / Google
                                                        │
                                                   ZenMux acts as a "translator":
                                                   no matter which model is behind it,
                                                   you use a single API Key for everything
```

Think of ZenMux as a universal remote — one remote that controls both OpenAI and Google TVs. The plugin translates Hermes' image requests into a format ZenMux understands, and ZenMux forwards them to the actual model.

> 💡 Two protocols: OpenAI models use `POST /v1/images/generations`, Google Gemini uses Vertex AI `generateContent`. But **you don't need to care about this** — the plugin handles it automatically.

---

## ❓ FAQ

**Q: Do I need separate OpenAI and Google accounts?**

A: No. One ZenMux account, one API Key, all models included.

**Q: Where are the generated images saved?**

A: Hermes auto-saves them to local cache. You'll see the image directly in chat.

**Q: Why is image generation sometimes slow?**

A: Depends on which model you pick. `gpt-image-2-high` is highest quality but can take up to 2 minutes. For daily use, `gpt-image-2` (15-40s) or `gemini` (10-30s) are recommended.

**Q: Can I use multiple models at the same time?**

A: Yes — different Threads can use different models without interfering. Thread A with GPT Image 2, Thread B with Gemini — just say "use Gemini to draw..." in your prompt.

---

## 📁 Project Structure

```
zenmux-image/
├── plugin.yaml              # Plugin metadata
├── __init__.py              # Plugin entry point (ImageGenProvider implementation)
├── README.md                # This document
├── README.zh-CN.md          # Chinese documentation
├── LICENSE                  # MIT
└── .gitignore
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)
