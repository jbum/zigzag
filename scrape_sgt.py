#!/usr/bin/env python3
"""
Scraper for Simon Tatham's Slant puzzles.
URL: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html

This script uses Selenium to scrape puzzles from the site.
The puzzle data is extracted from the permalink URL which contains the dimensions and givens.

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

# SGT Slant presets: (name, width, height, difficulty_code)
# Based on actual Simon Tatham puzzle presets found on the site
SGT_PRESETS = [
    ("5x5 Easy", 5, 5, "easy"),
    ("5x5 Hard", 5, 5, "hard"),
    ("8x8 Easy", 8, 8, "easy"),
    ("8x8 Hard", 8, 8, "hard"),
    ("12x10 Easy", 12, 10, "easy"),
    ("12x10 Hard", 12, 10, "hard"),
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


def parse_puzzle_id(puzzle_id):
    """
    Parse puzzle dimensions and givens from puzzle ID.
    Format: WxH:givens
    Example: 8x8:c120a0b21h3a2114f3a2b2a4b2110a1a1b1c2132d1b1a33a1a1c0b
    """
    match = re.search(r'^(\d+)x(\d+):(.+)$', puzzle_id)
    if match:
        width = int(match.group(1))
        height = int(match.group(2))
        givens = match.group(3)
        return width, height, givens
    return None, None, None


def count_givens(givens_str):
    """Count the number of clue digits (0-4) in the givens string."""
    return sum(1 for c in givens_str if c in '01234')


def select_preset(driver, preset_name):
    """
    Select a preset from the Type menu.

    Args:
        driver: Selenium WebDriver
        preset_name: Name of the preset (e.g., "5x5 Easy")

    Returns:
        True if successful, False otherwise
    """
    try:
        # Find and click the Type menu item
        menu_items = driver.find_elements(By.CSS_SELECTOR, "#gamemenu > ul > li")
        type_menu = None
        for item in menu_items:
            if "Type" in item.text:
                type_menu = item
                break

        if not type_menu:
            print("Could not find Type menu")
            return False

        type_menu.click()
        time.sleep(0.3)

        # Find the preset in the submenu
        submenu_items = driver.find_elements(By.CSS_SELECTOR, "#gamemenu ul ul li")
        for item in submenu_items:
            if item.text.strip() == preset_name:
                item.click()
                time.sleep(1)  # Wait for puzzle to generate
                return True

        print(f"Could not find preset '{preset_name}' in submenu")
        return False

    except Exception as e:
        print(f"Error selecting preset {preset_name}: {e}")
        return False


def scrape_puzzles(driver, preset_name, num_puzzles=10):
    """
    Scrape puzzles for a given preset.

    Args:
        driver: Selenium WebDriver
        preset_name: Name of the preset (e.g., "5x5 Easy")
        num_puzzles: Number of puzzles to scrape

    Returns:
        List of puzzle tuples: (title, width, height, givens, answer, comment)
    """
    puzzles = []
    base_url = "https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html"

    # Navigate to the page
    driver.get(base_url)
    time.sleep(2)  # Wait for page to load

    if not select_preset(driver, preset_name):
        return puzzles

    # Generate puzzles
    for i in range(num_puzzles):
        try:
            # Open Game menu and click "Enter game ID..." to get the puzzle data
            menu_items = driver.find_elements(By.CSS_SELECTOR, "#gamemenu > ul > li")
            for item in menu_items:
                if "Game" in item.text:
                    item.click()
                    time.sleep(0.3)
                    break

            # Find "Enter game ID..." option
            submenu_items = driver.find_elements(By.CSS_SELECTOR, "#gamemenu ul ul li")
            for item in submenu_items:
                if "game ID" in item.text:
                    item.click()
                    time.sleep(0.3)
                    break

            # Get the puzzle ID from the input field
            url_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            puzzle_id = url_input.get_attribute("value")

            # Close the dialog by clicking Cancel or pressing Escape
            try:
                cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel')]")
                cancel_btn.click()
            except:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

            time.sleep(0.3)

            # Parse the puzzle ID
            width, height, givens = parse_puzzle_id(puzzle_id)

            if width and height and givens:
                # Create puzzle title
                difficulty = "easy" if "Easy" in preset_name else "hard"
                title = f"SGT_{width}x{height}_{difficulty}_{i+1}"
                num_clues = count_givens(givens)
                comment = f"# givens={num_clues}"

                puzzles.append((title, width, height, givens, "", comment))
                print(f"  Scraped: {title}")

            # Click "New game" to generate a new puzzle
            if i < num_puzzles - 1:
                new_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "new"))
                )
                new_button.click()
                time.sleep(1)  # Wait for new puzzle to generate

        except Exception as e:
            print(f"  Error scraping puzzle {i+1}: {e}")
            # Try to recover by clicking elsewhere to close any dialog
            try:
                driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(0.5)
                new_button = driver.find_element(By.ID, "new")
                new_button.click()
                time.sleep(1)
            except:
                pass

    return puzzles


def main():
    parser = argparse.ArgumentParser(description="Scrape Slant puzzles from Simon Tatham's site")
    parser.add_argument("-n", "--num", type=int, default=10,
                        help="Number of puzzles per preset (default: 10)")
    parser.add_argument("-o", "--output", type=str,
                        default="./testsuites/SGT_testsuite.txt",
                        help="Output file path")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run browser in headless mode (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless",
                        help="Run browser with visible window")
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print("Starting SGT Slant puzzle scraper...")
    print(f"Will scrape {args.num} puzzles for each of {len(SGT_PRESETS)} presets")

    driver = setup_driver(headless=args.headless)
    all_puzzles = []

    try:
        for preset_name, width, height, difficulty in SGT_PRESETS:
            print(f"\nScraping preset: {preset_name}")
            puzzles = scrape_puzzles(driver, preset_name, args.num)
            all_puzzles.extend(puzzles)
            print(f"  Total scraped for this preset: {len(puzzles)}")
    finally:
        driver.quit()

    # Write to output file
    print(f"\nWriting {len(all_puzzles)} puzzles to {args.output}")
    with open(args.output, 'w') as f:
        f.write("# SGT Slant Testsuite\n")
        f.write("# Scraped from https://www.chiark.greenend.org.uk/~sgtatham/puzzles/js/slant.html\n")
        f.write("# Format: title<tab>width<tab>height<tab>givens<tab>answer<tab>comment\n")
        f.write("\n")
        for title, width, height, givens, answer, comment in all_puzzles:
            f.write(f"{title}\t{width}\t{height}\t{givens}\t{answer}\t{comment}\n")

    print(f"Done! Scraped {len(all_puzzles)} puzzles total.")


if __name__ == "__main__":
    main()
