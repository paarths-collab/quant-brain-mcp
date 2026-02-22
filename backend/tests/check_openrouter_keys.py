import os
import httpx
import asyncio

KEYS = [
    "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",
    "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"
]

MODEL = "qwen/qwen3-vl-235b-a22b-thinking"

async def check_key(key, index):
    print(f"Checking Key #{index + 1}: {key[:15]}...")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://boomerang-agentic.com", # Required by OpenRouter
        "X-Title": "Boomerang Agentic"
    }
    
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "max_tokens": 10
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if resp.status_code == 200:
                print(f"✅ Key #{index + 1} working! Response: {resp.json()['choices'][0]['message']['content']}")
                return True
            else:
                print(f"❌ Key #{index + 1} failed. Status: {resp.status_code}, Error: {resp.text}")
                return False
    except Exception as e:
        print(f"❌ Key #{index + 1} error: {str(e)}")
        return False

async def main():
    print(f"Testing {len(KEYS)} keys against model: {MODEL}\n")
    
    with open("openrouter_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Testing {len(KEYS)} keys against model: {MODEL}\n\n")
        
        for i, key in enumerate(KEYS):
            result = await check_key(key, i)
            status_msg = f"Key #{i + 1}: {'✅ Working' if result else '❌ Failed'}\n"
            f.write(status_msg)
            print("-" * 50)
            f.write("-" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
