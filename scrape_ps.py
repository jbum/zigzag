#!/usr/bin/env python3
"""
Scraper for puzzle-slant.com puzzles.
URL: https://www.puzzle-slant.com/

This script uses Selenium to scrape puzzles from the site.
The puzzle data is extracted from JavaScript variables in the page.

Output format (tab-delimited):
    puzzle-title    width   height  givens  answer  comment
"""

import argparse
import os
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# PS Slant presets: (name, size_param, width, height, difficulty)
# Based on URL parameters: ?size=N
PS_PRESETS = [
    ("5x5 Easy", 0, 5, 5, "easy"),
    ("5x5 Normal", 1, 5, 5, "normal"),
    ("7x7 Easy", 2, 7, 7, "easy"),
    ("7x7 Normal", 3, 7, 7, "normal"),
    ("10x10 Easy", 4, 10, 10, "easy"),
    ("10x10 Normal", 5, 10, 10, "normal"),
    ("15x15 Easy", 6, 15, 15, "easy"),
    ("15x15 Normal", 7, 15, 15, "normal"),
    ("20x20 Easy", 8, 20, 20, "easy"),
    ("20x20 Normal", 9, 20, 20, "normal"),
]


def setup_driver(headless=True):
    """Set up Chrome WebDriver with options."""
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,900")
    driver = webdriver.Chrome(options=options)
    return driver


def count_givens(givens_str):
    """Count the number of clue digits (0-4) in the givens string."""
    return sum(1 for c in givens_str if c in '01234')


def extract_puzzle_data(driver):
    """
    Extract puzzle data from JavaScript variables and page source.

    Returns:
        tuple: (width, height, givens) or (None, None, None) if failed
    """
    try:
        # Get the task variable from JavaScript (this works directly)
        task = driver.execute_script("return window.task;")

        # Get width/height from page source (they're in an object literal, not global vars)
        page_source = driver.page_source
        pw_match = re.search(r"puzzleWidth['\"]?\s*[:=]\s*(\d+)", page_source)
        ph_match = re.search(r"puzzleHeight['\"]?\s*[:=]\s*(\d+)", page_source)

        if task and pw_match and ph_match:
            width = int(pw_match.group(1))
            height = int(ph_match.group(1))
            return width, height, task

    except Exception as e:
        print(f"    Error extracting puzzle data: {e}")

    return None, None, None


def scrape_puzzles(driver, preset_name, size_param, num_puzzles=10):
    """
    Scrape puzzles for a given preset.

    Args:
        driver: Selenium WebDriver
        preset_name: Name of the preset (e.g., "5x5 Easy")
        size_param: URL size parameter (0-9)
        num_puzzles: Number of puzzles to scrape

    Returns:
        List of puzzle tuples: (title, width, height, givens, answer, comment)
    """
    puzzles = []
    base_url = f"https://www.puzzle-slant.com/?size={size_param}"

    for i in range(num_puzzles):
        try:
            # Navigate to the page (each load generates a new puzzle)
            driver.get(base_url)
            time.sleep(2)  # Wait for page to fully load

            # Extract puzzle data from JavaScript
            width, height, givens = extract_puzzle_data(driver)

            if width and height and givens:
                # Create puzzle title
                difficulty = "easy" if "Easy" in preset_name else "normal"
                title = f"PS_{width}x{height}_{difficulty}_{i+1}"
                num_clues = count_givens(givens)
                comment = f"# givens={num_clues}"

                puzzles.append((title, width, height, givens, "", comment))
                print(f"  Scraped: {title}")
            else:
                print(f"  Failed to extract puzzle {i+1}")

        except Exception as e:
            print(f"  Error scraping puzzle {i+1}: {e}")

    return puzzles


def main():
    parser = argparse.ArgumentParser(description="Scrape Slant puzzles from puzzle-slant.com")
    parser.add_argument("-n", "--num", type=int, default=10,
                        help="Number of puzzles per preset (default: 10)")
    parser.add_argument("-o", "--output", type=str,
                        default="./testsuites/PS_testsuite.txt",
                        help="Output file path")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser in headless mode (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless",
                        help="Run browser with visible window")
    parser.add_argument("--sizes", type=str, default=None,
                        help="Comma-separated list of size indices to scrape (0-9), e.g. '0,1,2,3'")
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Filter presets if --sizes specified
    presets = PS_PRESETS
    if args.sizes:
        size_indices = [int(x) for x in args.sizes.split(',')]
        presets = [p for p in PS_PRESETS if p[1] in size_indices]

    print("Starting puzzle-slant.com puzzle scraper...")
    print(f"Will scrape {args.num} puzzles for each of {len(presets)} presets")

    driver = setup_driver(headless=args.headless)
    all_puzzles = []

    try:
        for preset_name, size_param, width, height, difficulty in presets:
            print(f"\nScraping preset: {preset_name}")
            puzzles = scrape_puzzles(driver, preset_name, size_param, args.num)
            all_puzzles.extend(puzzles)
            print(f"  Total scraped for this preset: {len(puzzles)}")
    finally:
        driver.quit()

    # Write to output file
    print(f"\nWriting {len(all_puzzles)} puzzles to {args.output}")
    with open(args.output, 'w') as f:
        f.write("# PS Slant Testsuite\n")
        f.write("# Scraped from https://www.puzzle-slant.com/\n")
        f.write("# Format: title<tab>width<tab>height<tab>givens<tab>answer<tab>comment\n")
        f.write("\n")
        for title, width, height, givens, answer, comment in all_puzzles:
            f.write(f"{title}\t{width}\t{height}\t{givens}\t{answer}\t{comment}\n")

    print(f"Done! Scraped {len(all_puzzles)} puzzles total.")


if __name__ == "__main__":
    main()
