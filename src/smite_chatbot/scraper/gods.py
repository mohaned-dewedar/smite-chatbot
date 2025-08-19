import asyncio
import json
import csv
from playwright.async_api import async_playwright
from urllib.parse import urljoin
import os
from datetime import datetime

class SmiteGodsScraper:
    def __init__(self, base_url="https://wiki.smite2.com/"):
        self.base_url = base_url
        self.gods_data = []
    
    async def scrape_gods(self, page_url="https://wiki.smite2.com/"):
        """
        Scrape gods data from the SMITE wiki page
        """
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                print(f"Navigating to: {page_url}")
                await page.goto(page_url, wait_until="networkidle")
                
                # Wait for the heroes container to load
                await page.wait_for_selector(".mp-heroes")
                
                # Find all god containers
                god_containers = await page.query_selector_all('.mp-heroes div[style*="display: inline-block"]')
                
                print(f"Found {len(god_containers)} god containers")
                
                for i, container in enumerate(god_containers):
                    try:
                        # Extract god name from title attribute
                        name_link = await container.query_selector('a[title]')
                        if not name_link:
                            continue
                            
                        god_name = await name_link.get_attribute('title')
                        profile_url = await name_link.get_attribute('href')
                        
                        # Make profile URL absolute
                        if profile_url and profile_url.startswith('/'):
                            profile_url = urljoin(self.base_url, profile_url)
                        
                        # Find god image 
                        images = await container.query_selector_all('img')
                        god_image_url = None
                        
                        for img in images:
                            src = await img.get_attribute('src')
                            if src and 'Transparent_God_Icon' not in src:
                                # Make image URL absolute
                                if src.startswith('/'):
                                    god_image_url = urljoin(self.base_url, src)
                                else:
                                    god_image_url = src
                                break
                        
                        if god_name:
                            god_data = {
                                'name': god_name,
                                'image_url': god_image_url or 'No image found',
                                'profile_url': profile_url or 'No URL found',
                                'index': i + 1
                            }
                            
                            self.gods_data.append(god_data)
                            print(f"Extracted: {god_name}")
                    
                    except Exception as e:
                        print(f"Error processing container {i}: {e}")
                        continue
                
                print(f"\nSuccessfully extracted {len(self.gods_data)} gods")
                
            except Exception as e:
                print(f"Error during scraping: {e}")
                raise
            
            finally:
                await browser.close()
    
    async def scrape_detailed_god_info(self, god_url):
        """
        Scrape additional details from individual god pages
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(god_url, wait_until="networkidle")
                
                # Extract additional information
                details = {}
                
                # Try to get god type/class
                try:
                    god_type = await page.query_selector('.god-info .god-type')
                    if god_type:
                        details['type'] = await god_type.inner_text()
                except:
                    pass
                
                # Try to get pantheon
                try:
                    pantheon = await page.query_selector('.infobox tr:has-text("Pantheon") td')
                    if pantheon:
                        details['pantheon'] = await pantheon.inner_text()
                except:
                    pass
                
                # Try to get role
                try:
                    role = await page.query_selector('.infobox tr:has-text("Type") td')
                    if role:
                        details['role'] = await role.inner_text()
                except:
                    pass
                
                return details
                
            except Exception as e:
                print(f"Error getting details for {god_url}: {e}")
                return {}
            
            finally:
                await browser.close()
    
    def save_to_json(self, filename="smite_gods.json"):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_gods': len(self.gods_data),
                'gods': self.gods_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")
    
    def save_to_csv(self, filename="smite_gods.csv"):
        """Save scraped data to CSV file"""
        if not self.gods_data:
            print("No data to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['index', 'name', 'image_url', 'profile_url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for god in self.gods_data:
                writer.writerow(god)
        
        print(f"Data saved to {filename}")
    
    def print_summary(self):
        """Print a summary of scraped data"""
        print(f"\n{'='*50}")
        print(f"SCRAPING SUMMARY")
        print(f"{'='*50}")
        print(f"Total gods found: {len(self.gods_data)}")
        print(f"{'='*50}")
        
        for god in self.gods_data[:10]:  # Show first 10
            print(f"{god['index']:2d}. {god['name']}")
        
        if len(self.gods_data) > 10:
            print(f"... and {len(self.gods_data) - 10} more")
    
    def get_gods_list(self):
        """Return list of god names"""
        return [god['name'] for god in self.gods_data]
    
    def get_images_list(self):
        """Return list of image URLs"""
        return [god['image_url'] for god in self.gods_data if god['image_url'] != 'No image found']

async def main():
    """Main function to run the scraper"""
    scraper = SmiteGodsScraper()
    
    print("Starting SMITE gods scraper...")
    print("="*50)
    
    # Scrape the main gods page
    await scraper.scrape_gods()
    
    # Print summary
    scraper.print_summary()
    
    # Save data
    scraper.save_to_json()
    scraper.save_to_csv()
    
    # Print some useful lists
    print(f"\nGod names list:")
    print(scraper.get_gods_list())
    
    print(f"\nImage URLs (first 5):")
    images = scraper.get_images_list()[:5]
    for img in images:
        print(img)
    
    return scraper

async def scrape_with_details():
    """Enhanced scraping with detailed god information"""
    scraper = SmiteGodsScraper()
    
    # First, get basic god info
    await scraper.scrape_gods()
    
    print("\nEnhancing with detailed information...")
    
    # Get detailed info for each god (limit to first 5 to avoid overwhelming the server)
    for god in scraper.gods_data[:5]:
        if god['profile_url'] != 'No URL found':
            print(f"Getting details for {god['name']}...")
            details = await scraper.scrape_detailed_god_info(god['profile_url'])
            god.update(details)
    
    scraper.save_to_json("smite_gods_detailed.json")
    
    return scraper

if __name__ == "__main__":
    
    
    # Run basic scraping
    scraper = asyncio.run(main())
    
   