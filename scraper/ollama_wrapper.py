# scraper/ollama_wrapper.py

from ollama import Client
import json
import logging
import re


class OllamaWrapper:
    def __init__(self, model_name="nous-hermes2", verbose=True):
        self.client = Client()
        self.model_name = model_name
        self.verbose = verbose

    import re

    def extract_abilities_from_html(self, raw_html: str) -> list:
        prompt = self._build_prompt(raw_html)

        if self.verbose:
            logging.info(f"Sending prompt to {self.model_name} model...")

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            raw_output = response['message']['content'].strip()

            if self.verbose:
                logging.debug(f"Raw LLM output:\n{raw_output}")

            # Extract first JSON block in output (safe fallback)
            json_str = self._extract_json_block(raw_output)
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from model response: {e}")
            logging.error(f"Raw model output:\n{raw_output}")
            return []

        except Exception as e:
            logging.error(f"LLM call failed: {e}")
            return []

    def _extract_json_block(self, text: str) -> str:
        """
        Extracts the first JSON array block from a string (fallback if extra content is present).
        """
        match = re.search(r"(\[\s*{.*?}\s*\])", text, re.DOTALL)
        if match:
            return match.group(1)
        return text.strip()


    def _build_prompt(self, html: str) -> str:
        try:
            with open("scraper/scraper_prompt.txt", "r", encoding="utf-8") as f:
                prompt = f.read()
            return prompt.format(html=html)
        except FileNotFoundError:
            raise RuntimeError("Prompt file not found. Make sure scraper_prompt.txt exists.")
        except KeyError:
            raise RuntimeError("Prompt file missing `{html}` placeholder for formatting.")


if __name__ == "__main__":
    from bs4 import BeautifulSoup
    import requests

    logging.basicConfig(level=logging.INFO)

    # Init wrapper with desired model
    llm = OllamaWrapper(model_name="granite3.2:8b", verbose=True)

    # Grab raw ability HTML from god page
    url = "https://wiki.smite2.com/w/Aladdin"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table", class_="wikitable")
    raw_html = "\n".join(str(table) for table in tables)

    # Extract structured data
    abilities = llm.extract_abilities_from_html(raw_html)

    # Output
    # Output results
    print("\nParsed Abilities:\n")
    for ability in abilities:
        print(f"- {ability['name']} ({ability['type']}): {ability['description'][:60]}...")