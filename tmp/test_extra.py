import asyncio
import aiohttp
from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.scorer import score_job
from scripts.location_utils import evaluate_job_location

async def test():
    async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0'}) as session:
        # ID 16237
        url1 = "https://jobs.smartrecruiters.com/Evolution/744000144608239"
        async with session.get(url1) as r:
            soup = BeautifulSoup(await r.text(), 'html.parser')
            text1 = soup.get_text(separator=' ')
        res1 = score_job(text1, title="Card Inspector (Quality Assurance)", location="Atlantic City, NJ, us", country="US", company="Evolution", url=url1)
        print("=== ID 16237 Evolution NJ ===")
        print("Score:", res1['score'])
        print("Disqualified:", res1['is_disqualified'], res1['disqualified_by'])

        # ID 16322
        url2 = "https://www.simplyhired.com/job/guP9tU_jT6-AGNvfIMfdRqfspU4xITKhtKpWVdgCa_ILgX9Z0zowcw"
        try:
            async with session.get(url2) as r:
                soup = BeautifulSoup(await r.text(), 'html.parser')
                text2 = soup.get_text(separator=' ')
            res2 = score_job(text2, title="Software Development Engineer in Test SDET", location="Seattle, WA", country="United States", company="Globenet", url=url2)
            print("=== ID 16322 SimplyHired Globenet ===")
            print("Score:", res2['score'])
            print("Disqualified:", res2['is_disqualified'], res2['disqualified_by'])
            print("Text sample:", text2[:400].encode('ascii', 'ignore').decode())
        except Exception as e:
            print("ID 16322 fetch error:", e)

asyncio.run(test())
