import os
import sys
import time
import json
import re
import webbrowser
import hashlib
import mss
import asyncio
import httpx
from PIL import Image
import pytesseract
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)


class PropSnatch:
    def __init__(self):
        self.used_codes = set()
        self.codes_redeemed = 0
        self.planid = 51  # Default plan_id

        # --- Optimizations ---
        # 1. Load config and cookies once
        self.config = json.load(open("assets/config.json", encoding="utf-8"))
        self.cookies = json.load(open("assets/cookies.json", encoding="utf-8"))

        # 2. Create a persistent, asynchronous HTTP session
        self.session = httpx.AsyncClient(cookies=self.cookies)

        # 3. Pre-compile regex patterns for speed
        self.code_patterns = [
            re.compile(r"USE CODE[:\s]+([A-Z0-9_]+)", re.IGNORECASE),
            re.compile(r"([A-Z]+\d+)", re.IGNORECASE),
            re.compile(r"([A-Z0-9_]*(?:25|50)[A-Z0-9_]*)", re.IGNORECASE),
            re.compile(r"([A-Z]+[0-9]+[A-Z]*)", re.IGNORECASE),
            re.compile(r"([A-Z0-9_]{4,})", re.IGNORECASE),
            re.compile(r"([A-Z0-9_]+)\s*[-:]", re.IGNORECASE),
        ]
        # --- End Optimizations ---

        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        self._clear_screen()
        self._print_banner()
        self._update_title()

    async def close_session(self):
        """Gracefully close the HTTP session."""
        await self.session.aclose()

    def _update_title(self):
        """Update the console title with current redemption count."""
        title = f"PropSnatch V1.0.0 (Optimized) | Codes Redeemed: {self.codes_redeemed}"
        os.system(f'title "{title}"')

    def _clear_screen(self):
        """Clear the console screen."""
        os.system("cls")

    def _print_banner(self):
        """Print the aesthetic banner."""
        banner = f"""{Fore.CYAN}██████╗ ██████╗  ██████╗ ██████╗ ███████╗███╗   ██╗ █████╗ ████████╗ ██████╗██╗  ██╗
██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║
██████╔╝██████╔╝██║   ██║██████╔╝███████╗██╔██╗ ██║███████║   ██║   ██║     ███████║
██╔═══╝ ██╔══██╗██║   ██║██╔═══╝ ╚════██║██║╚██╗██║██╔══██║   ██║   ██║     ██╔══██║
██║     ██║  ██║╚██████╔╝██║     ███████║██║ ╚████║██║  ██║   ██║   ╚██████╗██║  ██║
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝{Style.RESET_ALL}"""
        print(banner)
        print(
            f"{Fore.GREEN}🎯 Ready to snatch those codes! (Owner Mode){Style.RESET_ALL}"
        )
        print(
            f"{Fore.BLUE}💡 Tip: Codes will be automatically detected and redeemed!{Style.RESET_ALL}"
        )

    def _extract_code(self, text):
        """Extract the actual code from detected text using pre-compiled regex."""
        for pattern in self.code_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # If the pattern has capturing groups, findall returns tuples
                code_candidate = match if isinstance(match, str) else match[0]
                code_upper = code_candidate.upper()

                if (
                    len(code_upper) >= 4
                    and code_upper
                    not in ["FREE", "RESETS", "ACCOUNTS", "SCALE", "CODE", "CODES"]
                    and any(c.isdigit() for c in code_upper)
                ):
                    # Basic OCR error correction
                    return code_upper.replace("S", "5").replace("O", "0")
        return None

    async def _process_detection(self, text):
        """Process OCR text and handle detections asynchronously."""
        if not text:
            return

        if "accounts" in text.lower() or "reset" in text.lower():
            extracted_code = self._extract_code(text)
            if extracted_code and extracted_code not in self.used_codes:
                self.used_codes.add(extracted_code)
                print(
                    f"{Fore.GREEN}{Style.BRIGHT}✨ Found new code: {extracted_code}{Style.RESET_ALL}"
                )
                # Run redemption in the background without blocking the scanner
                asyncio.create_task(
                    self.redeem(coupon_code=extracted_code, detected_text=text)
                )

    async def _scan(self):
        """Scan the screen for codes and process them."""
        input(
            f"{Fore.YELLOW}\nPress Enter to start scanning for codes...{Style.RESET_ALL}"
        )
        print(f"{Fore.GREEN}🔍 Starting code detection...\n{Style.RESET_ALL}")

        region = self.config.get(
            "scan_region", {"top": 929, "left": 23, "width": 1448, "height": 124}
        )

        with mss.mss() as sct:
            while True:
                try:
                    sct_img = sct.grab(region)
                    screenshot = Image.frombytes(
                        "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
                    )

                    text = pytesseract.image_to_string(
                        screenshot, config="--psm 6"
                    ).strip()

                    if not text:
                        await asyncio.sleep(0.5)  # Shorter sleep when idle
                        continue

                    if self.config.get("debug", False):
                        print(
                            f"{Fore.CYAN}📱 Detected text: {Style.DIM}{text.upper()}{Style.RESET_ALL}"
                        )

                    await self._process_detection(text)
                    await asyncio.sleep(0.1)  # Very short sleep to yield control

                except mss.exception.ScreenShotError as e:
                    print(
                        f"{Fore.RED}💥 ERROR! Failed to grab screenshot: {e}{Style.RESET_ALL}"
                    )
                    await asyncio.sleep(5)
                except Exception as e:
                    print(
                        f"{Fore.RED}💥 An unexpected error occurred in the scan loop: {e}{Style.RESET_ALL}"
                    )
                    await asyncio.sleep(5)

    async def redeem(self, coupon_code: str, detected_text: str = ""):
        """Asynchronously redeem a coupon code."""
        print(
            f"{Fore.BLUE}🚀 Attempting to redeem code: {Style.BRIGHT}{coupon_code}{Style.RESET_ALL}"
        )

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
            "content-type": "application/json",
            "origin": "https://myfundedfutures.com",
            "priority": "u=1, i",
            "referer": "https://myfundedfutures.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        }

        # Determine planid based on detected text
        detected_upper = detected_text.upper()
        if "ACCOUNTS" in detected_upper:
            if "50K SCALE" in detected_upper:
                self.planid = 52
            elif "100K SCALE" in detected_upper:
                self.planid = 53
            elif "150K SCALE" in detected_upper:
                self.planid = 54
            elif "50K CORE" in detected_upper:
                self.planid = 51
            elif "50K PRO" in detected_upper:
                self.planid = 48
            elif "100K PRO" in detected_upper:
                self.planid = 49
            elif "150K PRO" in detected_upper:
                self.planid = 50

        if "FREE RESETS" in detected_upper:
            print(f"{Fore.YELLOW}ℹ️ Skipping 'FREE RESETS' code.{Style.RESET_ALL}")
            return

        json_data = {
            "affiliateCampaign": "",
            "affiliateId": "",
            "affiliateSource": "",
            "competitionId": None,
            "couponCode": coupon_code,  # coupon_code
            "isActivation": False,
            "isMarketData": False,
            "isRenewal": False,
            "isReset": False,
            "isSimFundedReset": False,
            "originalAccountId": None,
            "plan_id": self.planid,
            "selectedBrokerage": "Tradovate",
            "selectedPlatform": "TradingView",
            "static_processor_id": 3,
            "subscriptionId": None,
        }

        try:
            response = await self.session.post(
                "https://api.myfundedfutures.com/api/initiateOneTimePayment/",
                headers=headers,
                json=json_data,
                timeout=10.0,
            )

            if response.status_code in [200, 204]:
                self.codes_redeemed += 1
                self._update_title()
                print(
                    f"{Fore.GREEN}{Style.BRIGHT}✅ SUCCESS! Code {coupon_code} redeemed! Total: {self.codes_redeemed}{Style.RESET_ALL}"
                )
                try:
                    response_data = response.json()
                    if "ok" in response_data and "redirect" in response_data["ok"]:
                        print(
                            f"{Fore.CYAN}🔗 Redirect URL: {response_data['ok']['redirect']}{Style.RESET_ALL}"
                        )
                except json.JSONDecodeError:
                    pass  # No JSON body, which is fine for 204 status
            else:
                print(
                    f"{Fore.RED}❌ FAILED! Code {coupon_code} redemption failed with status: {response.status_code}{Style.RESET_ALL}"
                )
                try:
                    print(f"{Fore.YELLOW}Response: {response.json()}{Style.RESET_ALL}")
                except json.JSONDecodeError:
                    print(f"{Fore.YELLOW}Response: {response.text}{Style.RESET_ALL}")

        except httpx.RequestError as e:
            print(
                f"{Fore.RED}💥 NETWORK ERROR! Could not reach the server: {e}{Style.RESET_ALL}"
            )
        except Exception as e:
            print(
                f"{Fore.RED}💥 REDEMPTION ERROR! An unexpected exception occurred: {e}{Style.RESET_ALL}"
            )
        finally:
            print(f"{Fore.CYAN}{'-' * 50}{Style.RESET_ALL}")


async def main():
    prop_snatch = PropSnatch()
    try:
        await prop_snatch._scan()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        await prop_snatch.close_session()


if __name__ == "__main__":
    asyncio.run(main())
