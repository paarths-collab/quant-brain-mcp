from backend.services.social_service import fetch_reddit_posts

def test_reddit():
    print("Testing Reddit Fetcher for NVDA...")
    data = fetch_reddit_posts("NVDA", limit=5)
    
    if "error" in data:
        print(f"Error: {data['error']}")
    else:
        print(f"Success! Found {len(data['posts'])} posts for {data['ticker']}")
        for post in data['posts']:
            print(f"- [{post['score']}] {post['title']} (r/{post['subreddit']})")

if __name__ == "__main__":
    test_reddit()
