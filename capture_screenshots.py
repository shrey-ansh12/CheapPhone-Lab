import asyncio
from playwright.async_api import async_playwright

async def capture_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        
        # 1. Dashboard
        await page.goto("http://localhost:5000/")
        await page.wait_for_timeout(1500)
        await page.screenshot(path="screenshots/dashboard.png")
        print("Captured dashboard.png")
        
        # 2. Test Lab
        await page.goto("http://localhost:5000/test-lab")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshots/test_lab.png")
        print("Captured test_lab.png")
        
        # 3. Test Runs
        await page.goto("http://localhost:5000/runs")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshots/test_runs.png")
        print("Captured test_runs.png")
        
        # 4. Failure Explorer
        await page.goto("http://localhost:5000/failures")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshots/failure_explorer.png")
        print("Captured failure_explorer.png")

        # 5. Impact Analysis
        await page.goto("http://localhost:5000/impact-analysis")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshots/impact_analysis.png")
        print("Captured impact_analysis.png")

        # 6. Graph Explorer
        await page.goto("http://localhost:5000/graph-explorer")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="screenshots/graph_explorer.png")
        print("Captured graph_explorer.png")

        # 7. Device Profiles
        await page.goto("http://localhost:5000/device-profiles")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="screenshots/device_profiles.png")
        print("Captured device_profiles.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_screenshots())
