# Hermes ZenMux 图片生成插件

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-≥%200.7.0-blue)](https://github.com/nousresearch/hermes-agent)

[English Version](./README.md) | 中文版本

让你的 Hermes AI 助手会画画——一个 API Key 同时用 OpenAI 和 Google Gemini 两家的图片生成模型。

---

## 😵‍💫 这是什么？

**一句话：** 这个插件让 Hermes 会生成图片。你说"画一只猫"，它就画一只猫。

Hermes 本身只是个文字助手，不会画画。这个插件给它接上了图片生成能力，用的是 [ZenMux](https://zenmux.ai/invite/1C3QLF) 的 API 网关。你只需要一个 ZenMux 的 API Key，就能用上两家的模型——不需要分别去 OpenAI 和 Google 注册。

---

## ✨ 它支持哪些模型？

| 模型 | 速度 | 适合场景 |
|------|------|---------|
| **GPT Image 2**（OpenAI） | ~15-40 秒 | 高质量、画面里能写字 |
| **GPT Image 2 High**（OpenAI） | ~40-120 秒 | 最高精度，慢但精致 |
| **Gemini 3.1 Flash Image**（Google） | ~10-30 秒 | 速度快，日常够用 |

---

## 🚀 快速上手（3 步）

### 前提条件

- ✅ 已经在用 [Hermes Agent](https://github.com/nousresearch/hermes-agent)（版本 ≥ 0.7.0）
- ✅ 有一个 [ZenMux](https://zenmux.ai/invite/1C3QLF) 账号和 API Key

---

### 第 1 步：安装插件

```bash
hermes plugins install colin-chang/hermes-plugin-zenmux-image --enable
```

### 第 2 步：配置 API Key

打开 `~/.hermes/.env`，添加一行：

```bash
ZENMUX_API_KEY=你的ZenMux密钥
```

### 第 3 步：配置图片生成后端

在 `~/.hermes/config.yaml` 中添加：

```yaml
image_gen:
  provider: zenmux
  zenmux:
    model: openai/gpt-image-2   # 默认模型，可以改成你想要的
```

重启 Hermes 后生效。现在对 Hermes 说"画一只戴皇冠的猫"试试。

---

## 📖 使用指南

### 基本用法

直接对 Hermes 说出你想画的东西就行，跟平时聊天一样：

> 画一幅赛博朋克风格的城市夜景，霓虹灯倒映在雨水中

> 生成一张海报：一只猫宇航员在月球上插中国国旗，写实风格

### 切换模型

**方式一：在提示词里直接说**（不用改配置）

- 说"用 **Gemini** 画一只猫" → 自动切到 Gemini
- 说"用 **OpenAI** 画一个城市" → 自动切到 GPT Image 2

**方式二：改配置文件**

```yaml
image_gen:
  zenmux:
    model: google/gemini-3.1-flash-image-preview
```

**方式三：环境变量**

```bash
export ZENMUX_IMAGE_MODEL=google/gemini-3.1-flash-image-preview
```

### 模型选择优先级

当多种方式同时存在时，优先级从高到低：

1. 提示词里的关键词（如"用 Gemini 画"→ 自动选 Gemini）
2. `ZENMUX_IMAGE_MODEL` 环境变量
3. `image_gen.zenmux.model` 配置文件
4. 默认模型：`openai/gpt-image-2`

---

## 🧱 它是怎么工作的？

一张大白话解释：

```
你说"画一只猫" ──→ Hermes Gateway ──→ 这个插件 ──→ ZenMux API ──→ OpenAI / Google
                                                         │
                                                    ZenMux 充当"翻译官"：
                                                    不管后面的模型是谁，
                                                    统一用一个 API Key 调用
```

ZenMux 就像一个万能遥控器——你只有一个遥控器，但能控制 OpenAI 和 Google 两家的电视。插件负责把 Hermes 的图片请求翻译成 ZenMux 能理解的格式，ZenMux 再转发给真正的模型。

> 💡 两个协议：OpenAI 的模型走 `POST /v1/images/generations`，Google Gemini 走 Vertex AI 的 `generateContent`。但**你不需要关心这些**——插件自动处理。

---

## ❓ 常见问题

**Q: 我需要分别注册 OpenAI 和 Google 的账号吗？**

A: 不需要。你只需要一个 ZenMux 账号，一个 API Key 就能用所有模型。

**Q: 图片保存在哪里？**

A: Hermes 会自动把生成的图片存到本地缓存，聊天里直接就能看到。

**Q: 为什么有时候图片生成很慢？**

A: 取决于你选哪个模型。`gpt-image-2-high` 最高质量，但可能要等 2 分钟。日常用推荐 `gpt-image-2`（15-40 秒）或 `gemini`（10-30 秒）。

**Q: 我能同时用好几个模型吗？**

A: 可以，在不同对话（Thread）里用不同模型互不影响。比如 Thread A 用 GPT Image 2，Thread B 用 Gemini——只需要在提示词里说"用 Gemini 画……"就行。

---

## 📁 项目结构

```
zenmux-image/
├── plugin.yaml              # 插件元数据
├── __init__.py              # 插件入口（ImageGenProvider 实现）
├── README.md                # 英文文档
├── README.zh-CN.md          # 本文档
├── LICENSE                  # MIT
└── .gitignore
```

---

## 📄 许可

MIT — 详见 [LICENSE](LICENSE)
