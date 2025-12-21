import asyncio
from twikit import Client, TooManyRequests
from datetime import datetime
import json
from random import randint

MINIMUM_TWEETS = 3000
QUERY = 'AMZN AAPL NVDA lang:en'


async def get_tweets(client, tweets):
    if tweets is None:
        print(f'{datetime.now()} - Getting tweets...')
        tweets = await client.search_tweet(QUERY, count=20, product='Latest')
    else:
        wait_time = randint(5, 10)
        print(f'{datetime.now()} - Getting next tweets after {wait_time} seconds ...')
        await asyncio.sleep(wait_time)
        tweets = await tweets.next()

    return tweets


async def main():
    # JSON init
    all_tweets = []

    client = Client(language='en-US', timeout=30)
    client.load_cookies('cookies.json')

    tweet_count = 0
    tweets = None

    while tweet_count < MINIMUM_TWEETS:

        try:
            tweets = await get_tweets(client, tweets)
        except TooManyRequests as e:
            reset_time = datetime.fromtimestamp(e.rate_limit_reset)
            print(f'{datetime.now()} - Rate limit reached. Waiting until {reset_time}')
            wait_time = (reset_time - datetime.now()).total_seconds()
            await asyncio.sleep(wait_time)
            continue

        if not tweets:
            print(f'{datetime.now()} - No more tweets found')
            break

        for tweet in tweets:
            tweet_count += 1

            data = {
                "Index": tweet_count,
                "Text": tweet.text,
                "CreatedAt": str(tweet.created_at),
                "RetweetCount": tweet.retweet_count,
                "ReplyCount": tweet.reply_count,
                "FavoriteCount": tweet.favorite_count,
                "QuoteCount": tweet.quote_count,
                "ViewCount": tweet.view_count
            }

            all_tweets.append(data)

        print(f'{datetime.now()} - Got {tweet_count} tweets')

    # Write JSON at the end
    with open('tweets.json', 'w', encoding='utf-8') as f:
        json.dump(all_tweets, f, ensure_ascii=False, indent=4)

    print(f'{datetime.now()} - Done! Got {tweet_count} tweets')


# Run async main()
asyncio.run(main())
