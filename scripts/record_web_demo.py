#!/usr/bin/env python3
"""Record a demo of the web interface using Playwright."""

import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def record_web_demo():
    """Record a demo of the Streamlit web interface."""
    # Start Streamlit server
    print("Starting Streamlit server...")
    server = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            "src/arxiv_to_ereader/web.py",
            "--server.port",
            "8502",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(5)

    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch()

            # Create context with video recording
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=".",
                record_video_size={"width": 1280, "height": 720},
            )

            page = context.new_page()

            print("Recording web demo...")

            # Navigate to the app
            page.goto("http://localhost:8502")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # Show the interface
            time.sleep(1)

            # Enter a paper ID
            input_field = page.get_by_placeholder("e.g., 2402.08954")
            input_field.click()
            time.sleep(0.5)

            # Type slowly for demo effect
            for char in "2402.08954":
                input_field.type(char, delay=100)
            time.sleep(1)

            # Press enter to trigger update
            input_field.press("Enter")
            time.sleep(1.5)

            # Show the format dropdown
            format_select = page.get_by_text("Output format").locator("..").locator("select, [data-baseweb='select']")
            if format_select.count() > 0:
                format_select.first.click()
                time.sleep(1)
                page.keyboard.press("Escape")

            time.sleep(1)

            # Hover over convert button
            convert_button = page.get_by_role("button", name="Convert to EPUB")
            convert_button.hover()
            time.sleep(1.5)

            # Close context to save video
            context.close()
            browser.close()

            # Get the video file
            video_path = page.video.path()
            print(f"Video saved to: {video_path}")

            # Convert to GIF using ffmpeg
            print("Converting to GIF...")
            output_gif = Path("demo-web.gif")
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", str(video_path),
                    "-vf", "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
                    "-loop", "0",
                    str(output_gif),
                ],
                check=True,
                capture_output=True,
            )

            # Clean up video file
            Path(video_path).unlink(missing_ok=True)

            print(f"Demo GIF saved to: {output_gif}")

    finally:
        # Stop server
        print("Stopping Streamlit server...")
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    record_web_demo()
