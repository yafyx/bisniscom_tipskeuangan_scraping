import json
import os
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def get_article_links(page_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(page_url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    article_links = []
    # Using a more general selector to capture all article links
    for article in soup.select(".artItem .artTitle"):
        # Find parent anchor tag that contains the link
        parent_link = article.find_parent("a")
        if parent_link and parent_link.get("href"):
            link = parent_link.get("href")
            if link and "read" in link and link not in article_links:
                article_links.append(link)

    # If the above selector didn't work, try an alternative approach
    if not article_links:
        for article in soup.select(".artItem"):
            links = article.select("a[href*='read']")
            for link_elem in links:
                link = link_elem.get("href")
                if link and link not in article_links:
                    article_links.append(link)

    print(f"Found {len(article_links)} article links")
    return article_links


def scrape_article_content(article_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(article_url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    title = soup.select_one("h1.article-title")
    if not title:
        title = soup.select_one("h1")
    title_text = title.get_text(strip=True) if title else "No Title"

    # Try to extract the date
    date_element = (
        soup.select_one("div.date")
        or soup.select_one("span.date")
        or soup.select_one("div.artDate")
    )
    date_str = None
    if date_element:
        date_str = date_element.get_text(strip=True)

    # Extract main content
    content_div = soup.select_one("article.detailsContent")
    if not content_div:
        content_div = soup.select_one(
            "div.article-body"
        )  # Fallback to previous selector

    content_text = ""
    if content_div:
        paragraphs = content_div.select("p")
        content_text = "\n".join(p.get_text(strip=True) for p in paragraphs)

    # Extract topic tags if available
    tags = []
    topics_section = soup.select_one("div.topic") or soup.select_one("ul.tags")
    if topics_section:
        tag_links = topics_section.select("a")
        tags = [
            tag.get_text(strip=True) for tag in tag_links if tag.get_text(strip=True)
        ]

    # If no tags were found, add default "tips keuangan" tag
    if not tags:
        tags = ["tips keuangan"]

    return {
        "title": title_text,
        "url": article_url,
        "content": content_text,
        "date": date_str,
        "tags": tags,
        "source": "bisnis.com",
    }


def scrape_bisnis_com():
    base_url = "https://www.bisnis.com/topic/28722/tips-keuangan/?page="
    all_articles_data = []

    # Iterate through pages 1 to 17
    for page in range(1, 18):
        page_url = f"{base_url}{page}"
        print(f"Scraping page {page}: {page_url}")

        # Get all article links from the current page
        article_links = get_article_links(page_url)
        print(f"Found {len(article_links)} articles on page {page}")

        # Scrape content from each article
        for link in article_links:
            try:
                article_data = scrape_article_content(link)
                all_articles_data.append(article_data)
                print(f"Successfully scraped: {article_data['title']}")
            except Exception as e:
                print(f"Error scraping {link}: {e}")

            # Add delay to avoid overwhelming the server
            time.sleep(1)

    return all_articles_data


def save_for_rag(articles, output_file="bisnis_tips_keuangan_data.json"):
    """Save the scraped articles in a format suitable for RAG chatbot consumption."""
    # Format data for RAG
    rag_data = []

    for article in articles:
        rag_document = {
            "id": hash(article["url"]),  # Generate a unique ID based on URL
            "title": article["title"],
            "content": article["content"],
            "metadata": {
                "source": article["source"],
                "url": article["url"],
                "date": article["date"],
                "tags": article["tags"],
            },
        }
        rag_data.append(rag_document)

    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Save to JSON file
    with open(os.path.join("output", output_file), "w", encoding="utf-8") as f:
        json.dump(rag_data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(rag_data)} articles to {output_file}")

    return os.path.join("output", output_file)


def main():
    articles = scrape_bisnis_com()

    # Display some statistics
    print(f"\nTotal articles scraped: {len(articles)}")

    # Print sample of articles
    if articles:
        print("\nSample of scraped articles:")
        for article in articles[:3]:
            print(f"Title: {article['title']}")
            print(f"URL: {article['url']}")
            print(f"Date: {article['date']}")
            print(f"Tags: {', '.join(article['tags'])}")
            print(f"Content Preview: {article['content'][:100]}...")
            print("-" * 50)

        # Save data for RAG
        output_file = save_for_rag(articles)
        print(f"\nData saved for RAG chatbot in: {output_file}")
    else:
        print(
            "No articles were scraped. Please check the website structure or network connection."
        )


if __name__ == "__main__":
    main()
