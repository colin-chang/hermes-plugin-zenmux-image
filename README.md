# hermes-plugin-zenmux-image

Hermes Agent image generation plugin for the [ZenMux](https://zenmux.ai/invite/1C3QLF) API gateway.

Supports **OpenAI gpt-image-2** and **Google Gemini** image generation models through a single ZenMux API key — no separate FAL, OpenAI, or Google Cloud subscriptions required.

## Supported Models

| Model ID | Protocol | Speed | Notes |
|----------|----------|-------|-------|
| `openai/gpt-image-2` | OpenAI Images API | ~15-40s | Default; high quality, text-in-image |
| `openai/gpt-image-2-high` | OpenAI Images API | ~40-120s | Highest fidelity |
| `google/gemini-3.1-flash-image-preview` | Vertex AI | ~10-30s | Fast, Google Gemini image gen |

## Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.7+
- A [ZenMux](https://zenmux.ai/invite/1C3QLF) API key

## Install

```bash
hermes plugins install colin-chang/hermes-plugin-zenmux-image --enable
```

Or install without enabling:

```bash
hermes plugins install colin-chang/hermes-plugin-zenmux-image
hermes plugins enable zenmux-image
```

## Configure

### 1. Add your ZenMux API key

Add to `~/.hermes/.env`:

```
ZENMUX_API_KEY=your_zenmux_api_key_here
```

### 2. Set the image generation provider

In `~/.hermes/config.yaml`:

```yaml
image_gen:
  provider: zenmux
  zenmux:
    model: openai/gpt-image-2   # default model
```

### 3. Enable the plugin

Make sure `plugins.enabled` includes the plugin:

```yaml
plugins:
  enabled:
    - zenmux-image
```

### 4. Restart Hermes

Start a new session for changes to take effect.

## Usage

Once configured, just ask Hermes to generate an image:

> 画一只戴着皇冠的三花猫

### Switching Models

**Via prompt keywords** (no config change needed):

- Say "用 **Gemini** 画一只猫" → routes to `google/gemini-3.1-flash-image-preview`
- Say "用 **OpenAI** 画一个城市" → routes to `openai/gpt-image-2`

**Via config:**

```yaml
image_gen:
  zenmux:
    model: google/gemini-3.1-flash-image-preview
```

**Via environment variable:**

```bash
export ZENMUX_IMAGE_MODEL=google/gemini-3.1-flash-image-preview
```

## Model Selection Priority

1. Explicit `model` parameter in tool call (if source patch is applied)
2. Prompt keyword hint (`gemini` / `openai` / `gpt-image`)
3. `ZENMUX_IMAGE_MODEL` environment variable
4. `image_gen.zenmux.model` in config.yaml
5. Default: `openai/gpt-image-2`

## Architecture

The plugin implements the `ImageGenProvider` ABC from Hermes Agent. Two API protocols are supported:

- **OpenAI Images API** (`POST /v1/images/generations`) — for gpt-image-2 models
- **Vertex AI generateContent** (`POST /vertex-ai/v1/models/…:generateContent`) — for Gemini models

Both are accessed through the ZenMux API gateway at `https://zenmux.ai/api/`.

## License

MIT
