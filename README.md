# 🤖 Facebook AI Tech News Bot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Gemini AI](https://img.shields.io/badge/Gemini-2.5_Flash-orange?style=for-the-badge&logo=google)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-green?style=for-the-badge&logo=githubactions)
![Facebook API](https://img.shields.io/badge/Facebook-Graph_API-1877F2?style=for-the-badge&logo=facebook)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**An AI-powered Python bot that automatically fetches tech news and publishes engaging posts in Moroccan Darija to a Facebook Page — fully automated via GitHub Actions.**

[Features](#-features) • [How It Works](#-how-it-works) • [Installation](#-installation) • [Configuration](#-configuration) • [Tech Stack](#-tech-stack) • [Author](#-author)

</div>

---

## 📌 Overview

This bot runs completely automatically twice a day via GitHub Actions. It fetches the latest technology news, generates an engaging post in Moroccan Darija using Gemini AI, finds a relevant image, and publishes everything to a Facebook Page — all without any manual intervention.

> 💡 **Goal:** Build an AI-driven tech news page that publishes quality content daily on autopilot.

---

## ✨ Features

- 🗞️ **Multi-source News Fetching** — NewsAPI as primary source + 24 RSS feeds as fallback
- 🤖 **AI-Generated Content** — Gemini 2.5 Flash writes natural Moroccan Darija posts
- 🖼️ **Smart Image System** — 4 fallback levels (Original → Unsplash API → Pexels API → Local Library)
- 🔁 **No Duplicate Posts** — Full tracking of published news and used images
- ⚡ **100% Automated** — GitHub Actions schedules and runs everything
- 🛡️ **Retry Logic** — Automatic retries on any API failure
- 📊 **Professional Logging** — Full visibility into every publishing cycle

---

## 🔄 How It Works

```
┌──────────────────────────────────────────────┐
│             GitHub Actions                   │
│         (Runs twice daily)                   │
└─────────────────┬────────────────────────────┘
                  │
     ┌────────────▼────────────┐
     │      Fetch News         │
     │  NewsAPI → RSS (backup) │
     └────────────┬────────────┘
                  │
     ┌────────────▼────────────┐
     │      Fetch Image        │
     │  1. Original (RSS)      │
     │  2. Unsplash API        │
     │  3. Pexels API          │
     │  4. Local Library       │
     └────────────┬────────────┘
                  │
     ┌────────────▼────────────┐
     │    Generate Post        │
     │    Gemini 2.5 Flash     │
     │    (Moroccan Darija)    │
     └────────────┬────────────┘
                  │
     ┌────────────▼────────────┐
     │   Publish to Facebook   │
     │   Facebook Graph API    │
     └────────────┬────────────┘
                  │
     ┌────────────▼────────────┐
     │       Save State        │
     │  posted_news.json       │
     │  sources_state.json     │
     │  used_images.json       │
     └─────────────────────────┘
```

---

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- A GitHub account
- A Facebook Page with publishing permissions

### 1. Clone the repository
```bash
git clone https://github.com/abdnorelamrani789-hash/facebook-ai-bot.git
cd facebook-ai-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Fill in your API keys
```

---

## ⚙️ Configuration

### Required Secrets (GitHub Repository Secrets)

| Secret | Description | Where to Get It |
|--------|-------------|-----------------|
| `FB_PAGE_ID` | Facebook Page ID | Page Settings |
| `FB_PAGE_ACCESS_TOKEN` | Facebook Page Access Token | [Meta for Developers](https://developers.facebook.com) |
| `GEMINI_API_KEY` | Google Gemini API Key | [Google AI Studio](https://aistudio.google.com) |
| `NEWS_API_KEY` | NewsAPI Key | [NewsAPI.org](https://newsapi.org) |
| `UNSPLASH_ACCESS_KEY` | Unsplash API Key | [Unsplash Developers](https://unsplash.com/developers) |
| `PEXELS_API_KEY` | Pexels API Key | [Pexels API](https://www.pexels.com/api) |
| `PAT_TOKEN` | GitHub Personal Access Token | GitHub → Settings → Developer settings |

### How to add Secrets
```
Repository → Settings → Secrets and variables → Actions → New repository secret
```

---

## 🚀 Usage

### Run manually
```bash
python bot.py
```

### Automated Schedule
The bot runs automatically via GitHub Actions:
- ☀️ **8:30 AM** (Morocco Time — UTC+1)
- 🌙 **6:30 PM** (Morocco Time — UTC+1)

### Trigger manually from GitHub
```
Actions tab → Tech News Bot → Run workflow → Run workflow
```

---

## 📁 Project Structure

```
facebook-ai-bot/
│
├── bot.py                  # Main bot logic
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
│
├── .github/
│   └── workflows/
│       └── automate.yml    # GitHub Actions workflow
│
├── posted_news.json        # Tracks published articles (auto-updated)
├── sources_state.json      # Tracks used RSS sources   (auto-updated)
└── used_images.json        # Tracks used images        (auto-updated)
```

---

## 🧰 Tech Stack

| Technology | Purpose |
|------------|---------|
| ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) | Core programming language |
| ![Gemini](https://img.shields.io/badge/-Gemini_2.5_Flash-orange?logo=google) | AI content generation in Moroccan Darija |
| ![GitHub Actions](https://img.shields.io/badge/-GitHub_Actions-2088FF?logo=githubactions&logoColor=white) | Automation & scheduling |
| ![Facebook](https://img.shields.io/badge/-Facebook_Graph_API-1877F2?logo=facebook&logoColor=white) | Publishing posts with images |
| ![NewsAPI](https://img.shields.io/badge/-NewsAPI-black) | Primary news source |
| ![Unsplash](https://img.shields.io/badge/-Unsplash-000000?logo=unsplash&logoColor=white) | High-quality images |
| ![Pexels](https://img.shields.io/badge/-Pexels-05A081?logo=pexels&logoColor=white) | Fallback image source |
| ![Feedparser](https://img.shields.io/badge/-Feedparser-grey) | RSS feed parsing |
| ![Pillow](https://img.shields.io/badge/-Pillow-blue) | Image processing & resizing |

---

## 📊 Sample Generated Post

```
راه وقع! Apple خرجات macOS 26.4 وجابت 4 features جديدة 🔥

كنحكيو على update مهم — مش مجرد bug fixes...

⚡ Siri Upgrade: دابا كيفهم السياق بشكل أحسن من قبل
⚡ Messages UI: واجهة جديدة أسهل وأسرع فالاستخدام
⚡ M3 Performance: أداء ملحوظ أحسن على MacBook M3

بالنسبة للمغاربة اللي عندهم Mac، هاد الـ update مجاني وكيستحق 💪

أنا شخصياً كنشوف بلي Apple كتحسن ببطء بصح بثبات...

أنتم واش غتحيّدو للـ macOS 26 ولا كتستنيو version أكثر استقراراً؟

#تقنية_بالدارجة #المغرب_التقني #Apple #macOS #تكنولوجيا
```

---

## 👤 Author

<div align="center">

### Abdennour Elamrani
**Networks & Systems Intern**

[![GitHub](https://img.shields.io/badge/GitHub-abdnorelamrani789--hash-181717?style=for-the-badge&logo=github)](https://github.com/abdnorelamrani789-hash)

</div>

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an Issue or submit a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Built with ❤️ in Morocco 🇲🇦

⭐ If you found this project useful, please give it a star!

</div>

