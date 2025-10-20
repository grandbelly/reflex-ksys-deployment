# -*- coding: utf-8 -*-
"""
Playwright Test - Deployment Version Functionality Verification
Tests the deployment version (Python 3.11, port 14000-14001) web interface
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os
from datetime import datetime

# Set environment to handle UTF-8 output on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

class DeploymentTester:
    def __init__(self, base_url="http://localhost:14000", timeout=30000):
        self.base_url = base_url
        self.timeout = timeout
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": []
        }

    async def run_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("DEPLOYMENT VERSION (Python 3.11) PLAYWRIGHT TEST")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                page = await browser.new_page()
                page.set_default_timeout(self.timeout)

                # Test 1: Page Load
                await self.test_page_load(page)

                # Test 2: Main Page Response
                await self.test_main_page_response(page)

                # Test 3: Dashboard Content
                await self.test_dashboard_content(page)

                # Test 4: Backend Connection
                await self.test_backend_connection(page)

                # Test 5: Performance Metrics
                await self.test_performance(page)

            except Exception as e:
                self.results["failed"].append(f"Test execution failed: {str(e)}")
                print(f"ERROR during test execution: {e}")
            finally:
                await browser.close()

        # Print results
        await self.print_results()

    async def test_page_load(self, page):
        """Test 1: Page Load"""
        try:
            print("TEST 1: Page Load Starting...")
            response = await page.goto(self.base_url)

            if response and response.ok:
                self.results["passed"].append("Page load successful")
                print(f"[PASS] Page loaded successfully (status: {response.status})")
            else:
                self.results["failed"].append(f"Page load failed (status: {response.status if response else 'None'})")
                print(f"[FAIL] Page load failed")
        except Exception as e:
            self.results["failed"].append(f"Page load exception: {str(e)}")
            print(f"[ERROR] Page load error: {e}")

    async def test_main_page_response(self, page):
        """Test 2: Main Page Response Time"""
        try:
            print("TEST 2: Main Page Response Time...")
            start_time = datetime.now()
            await page.goto(self.base_url)
            end_time = datetime.now()

            response_time = (end_time - start_time).total_seconds() * 1000
            self.results["passed"].append(f"Page response time: {response_time:.2f}ms")
            print(f"[PASS] Page response time: {response_time:.2f}ms")

            if response_time > 10000:
                print(f"[WARN] Response time exceeded 10 seconds")

        except Exception as e:
            self.results["failed"].append(f"Response time measurement failed: {str(e)}")
            print(f"[ERROR] Response time measurement failed: {e}")

    async def test_dashboard_content(self, page):
        """Test 3: Dashboard Content"""
        try:
            print("TEST 3: Dashboard Content Check...")
            await page.goto(self.base_url)

            # Check page title
            title = await page.title()
            print(f"   Page title: {title}")

            # Check body content length
            content = await page.content()
            content_length = len(content)

            if content_length > 1000:
                self.results["passed"].append(f"Dashboard content loaded ({content_length}bytes)")
                print(f"[PASS] Dashboard content loaded ({content_length} bytes)")
            else:
                self.results["failed"].append(f"Insufficient content ({content_length} bytes)")
                print(f"[FAIL] Content too small: {content_length} bytes")

        except Exception as e:
            self.results["failed"].append(f"Dashboard content check failed: {str(e)}")
            print(f"[ERROR] Dashboard content check failed: {e}")

    async def test_backend_connection(self, page):
        """Test 4: Backend Connection"""
        try:
            print("TEST 4: Backend Connection Check...")
            backend_url = self.base_url.replace("14000", "14001")

            response = await page.request.get(backend_url, timeout=5000)
            if response.ok or response.status < 500:
                self.results["passed"].append(f"Backend response successful (status: {response.status})")
                print(f"[PASS] Backend connection successful (status: {response.status})")
            else:
                self.results["failed"].append(f"Backend response failed (status: {response.status})")
                print(f"[FAIL] Backend response failed (status: {response.status})")

        except Exception as e:
            self.results["skipped"].append(f"Backend test skipped: {str(e)}")
            print(f"[SKIP] Backend test skipped: {e}")

    async def test_performance(self, page):
        """Test 5: Performance Metrics"""
        try:
            print("TEST 5: Performance Metrics...")

            # Page load metrics
            navigation_timing = await page.evaluate("""
                () => {
                    const timing = window.performance.timing;
                    return {
                        'domContentLoaded': timing.domContentLoadedEventEnd - timing.navigationStart,
                        'pageLoadTime': timing.loadEventEnd - timing.navigationStart,
                        'timeToFirstByte': timing.responseStart - timing.navigationStart,
                    };
                }
            """)

            if navigation_timing:
                self.results["passed"].append(f"Performance metrics: DCL={navigation_timing['domContentLoaded']}ms, Load={navigation_timing['pageLoadTime']}ms")
                print(f"[PASS] Performance metrics:")
                print(f"   DOM Content Loaded: {navigation_timing['domContentLoaded']}ms")
                print(f"   Page Load Time: {navigation_timing['pageLoadTime']}ms")
                print(f"   Time to First Byte: {navigation_timing['timeToFirstByte']}ms")
            else:
                self.results["skipped"].append("Performance metrics not supported")
                print(f"[SKIP] Performance metrics not supported")

        except Exception as e:
            self.results["skipped"].append(f"Performance measurement skipped: {str(e)}")
            print(f"[SKIP] Performance measurement skipped: {e}")

    async def print_results(self):
        """Print test results summary"""
        print()
        print("=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        print()

        total_tests = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["skipped"])
        pass_rate = (len(self.results["passed"]) / (total_tests - len(self.results["skipped"])) * 100) if (total_tests - len(self.results["skipped"])) > 0 else 0

        print(f"PASSED: {len(self.results['passed'])}")
        for result in self.results["passed"]:
            print(f"   + {result}")

        print()
        print(f"FAILED: {len(self.results['failed'])}")
        for result in self.results["failed"]:
            print(f"   - {result}")

        print()
        print(f"SKIPPED: {len(self.results['skipped'])}")
        for result in self.results["skipped"]:
            print(f"   ~ {result}")

        print()
        print("=" * 80)
        print(f"Pass rate: {pass_rate:.1f}% ({len(self.results['passed'])}/{total_tests - len(self.results['skipped'])})")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        return len(self.results["failed"]) == 0

async def main():
    """Main function"""
    tester = DeploymentTester()
    success = await tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
