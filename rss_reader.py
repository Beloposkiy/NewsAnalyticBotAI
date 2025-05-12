import feedparser

def get_rss_news(rss_url: str, limit=5):
    feed = feedparser.parse(rss_url)
    news = []

    for entry in feed.entries[:limit]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        published = entry.get("published", "")
        summary = entry.get("summary", "")
        news.append(f"📰 <b>{title}</b>\n🗓 {published}\n🔗 <a href=\"{link}\">Читать</a>")

    return news