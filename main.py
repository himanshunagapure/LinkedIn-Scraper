"""
LinkedIn Scraper - Main Interface
Simple one-line usage: linkedin_scraper(urls)

Usage:
    from main import linkedin_scraper
    
    urls = [
        "https://www.linkedin.com/in/williamhgates/",
        "https://www.linkedin.com/company/microsoft/",
        "https://www.linkedin.com/posts/aiqod_inside-aiqod-how-were-building-enterprise-ready-activity-7348224698146541568-N7oQ",
        "https://www.linkedin.com/newsletters/aiqod-insider-7325820451622940672"
    ]
    
    results = linkedin_scraper(urls)
"""

import asyncio
import json
import time
import re
from typing import List, Dict, Any, Optional
from linkedin_data_extractor_v1 import LinkedInDataExtractor


class LinkedInScraperMain:
    """Main LinkedIn Scraper class with simplified interface"""
    
    def __init__(self, headless: bool = True, enable_anti_detection: bool = True):
        self.headless = headless
        self.enable_anti_detection = enable_anti_detection
        self.extractor = None
    
    async def scrape_async(self, urls: List[str], output_filename: str = "linkedin_scraped_data.json") -> Dict[str, Any]:
        """Async method to scrape LinkedIn URLs"""
        
        print("=" * 80)
        print("🚀 LINKEDIN SCRAPER - STARTING")
        print("=" * 80)
        print(f"📋 URLs to scrape: {len(urls)}")
        print(f"📁 Output file: {output_filename}")
        print("=" * 80)
        
        # Initialize extractor
        self.extractor = LinkedInDataExtractor(
            headless=self.headless, 
            enable_anti_detection=self.enable_anti_detection
        )
        
        results = {
            "scraping_metadata": {
                "timestamp": time.time(),
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_urls": len(urls),
                "successful_scrapes": 0,
                "failed_scrapes": 0,
                "scraper_version": "linkedin_scraper_main_v1.0"
            },
            "scraped_data": [],
            "failed_urls": []
        }
        
        try:
            await self.extractor.start()
            print("✅ LinkedIn scraper initialized successfully")
            
            for i, url in enumerate(urls, 1):
                print(f"\n{'='*60}")
                print(f"🔍 SCRAPING {i}/{len(urls)}: {url}")
                print(f"{'='*60}")
                
                try:
                    # Extract raw data
                    raw_data = await self.extractor.extract_linkedin_data(url)
                    
                    if raw_data.get('error'):
                        print(f"❌ Failed to scrape {url}: {raw_data['error']}")
                        results["failed_urls"].append({
                            "url": url,
                            "error": raw_data['error']
                        })
                        results["scraping_metadata"]["failed_scrapes"] += 1
                        continue
                    
                    # Process and structure data
                    structured_data = self._structure_linkedin_data(raw_data)
                    
                    if structured_data:
                        results["scraped_data"].append(structured_data)
                        results["scraping_metadata"]["successful_scrapes"] += 1
                        print(f"✅ Successfully scraped: {structured_data.get('full_name', 'Unknown')}")
                    else:
                        print(f"❌ Failed to structure data for {url}")
                        results["failed_urls"].append({
                            "url": url,
                            "error": "Failed to structure data"
                        })
                        results["scraping_metadata"]["failed_scrapes"] += 1
                
                except Exception as e:
                    print(f"❌ Error scraping {url}: {str(e)}")
                    results["failed_urls"].append({
                        "url": url,
                        "error": str(e)
                    })
                    results["scraping_metadata"]["failed_scrapes"] += 1
                
                # Brief pause between requests
                await asyncio.sleep(2)
            
            # Save results to file
            self._save_results_to_file(results, output_filename)
            
            # Print summary
            self._print_summary(results)
            
            return results
        
        except Exception as e:
            print(f"❌ Critical error in LinkedIn scraper: {e}")
            raise
        
        finally:
            if self.extractor:
                await self.extractor.stop()
                print("🔧 LinkedIn scraper cleanup completed")
    
    def _structure_linkedin_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Structure raw LinkedIn data according to requirements"""
        
        url = raw_data.get('url', '')
        url_type = raw_data.get('url_type', 'unknown')
        
        # Get combined data (primary source)
        combined_data = raw_data.get('extracted_data', {})
        
        # Get fallback data
        json_ld_data = raw_data.get('json_ld_data', {}).get('parsed_data', {})
        meta_data = raw_data.get('meta_data', {})
        
        # Base structure
        structured = {
            "url": url,
            "url_type": url_type,
            "scraping_timestamp": time.time(),
            "scraping_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Structure data based on URL type
        if url_type == "profile":
            structured.update(self._structure_profile_data(combined_data, json_ld_data, meta_data, url))
        
        elif url_type == "company":
            structured.update(self._structure_company_data(combined_data, json_ld_data, meta_data, url))
        
        elif url_type == "post":
            structured.update(self._structure_post_data(combined_data, json_ld_data, meta_data, url))
        
        elif url_type == "newsletter":
            structured.update(self._structure_newsletter_data(combined_data, json_ld_data, meta_data, url))
        
        else:
            # Generic structure
            structured.update(self._structure_generic_data(combined_data, json_ld_data, meta_data, url))
        
        return structured if self._has_meaningful_data(structured) else None
    
    def _structure_profile_data(self, combined: Dict, json_ld: Dict, meta: Dict, url: str) -> Dict[str, Any]:
        """Structure profile data"""
        
        # Extract username from URL
        username_match = re.search(r'linkedin\.com/in/([^/?]+)', url)
        username = username_match.group(1) if username_match else ""
        
        return {
            "username": username,
            "full_name": self._get_reliable_value([
                combined.get('name'),
                json_ld.get('name'),
                meta.get('open_graph', {}).get('og:title', '').split(' | ')[0] if ' | ' in meta.get('open_graph', {}).get('og:title', '') else meta.get('open_graph', {}).get('og:title'),
                meta.get('title', '').split(' | ')[0] if ' | ' in meta.get('title', '') else meta.get('title')
            ]),
            "job_title": self._get_reliable_value([
                combined.get('job_title'),
                json_ld.get('job_title'),
                self._extract_title_from_meta(meta)
            ]),
            "title": self._get_reliable_value([
                meta.get("title").split(" - ", 1)[-1].split(" | ", 1)[0]
            ]),
            "followers": self._get_reliable_value([
                combined.get('followers'),
                json_ld.get('followers'),
                combined.get('author_followers')
            ], convert_to_int=True),
            "connections": self._get_reliable_value([
                combined.get('connections')
            ], convert_to_int=True),
            "about": self._get_reliable_value([
                combined.get('description'),
                json_ld.get('description'),
                meta.get('open_graph', {}).get('og:description'),
                meta.get('description')
            ]),
            "location": self._get_reliable_value([
                combined.get('location'),
                json_ld.get('location'),
                combined.get('country')
            ]),
            "website": self._get_reliable_value([
                combined.get('same_as'),
                json_ld.get('same_as'),
                combined.get('url')
            ]),
            "contact_info": {}  # Not typically available in public data
        }
    
    def _structure_company_data(self, combined: Dict, json_ld: Dict, meta: Dict, url: str) -> Dict[str, Any]:
        """Structure company data"""
        
        # Extract username from URL
        username_match = re.search(r'linkedin\.com/company/([^/?]+)', url)
        username = username_match.group(1) if username_match else ""
        return {
            "username": username,
            "full_name": self._get_reliable_value([
                json_ld.get('name'),
                combined.get('name'),
                meta.get('title', '').split(' | ')[0] if ' | ' in meta.get('title', '') else meta.get('title')
            ]),
            "address": self._format_company_address(json_ld.get('address', {})),
            "website": self._get_reliable_value([
                combined.get('same_as'),
                json_ld.get('same_as')
            ]),
            "about_us": self._get_reliable_value([
                json_ld.get('description')
            ]),
            "employee_count": self._get_reliable_value([
                json_ld.get('employee_count')
            ], convert_to_int=True)
        }
    
    def _structure_post_data(self, combined: Dict, json_ld: Dict, meta: Dict, url: str) -> Dict[str, Any]:
        """Structure post data"""
        
        return {
            "url": url,
            "headline": self._get_reliable_value([
                combined.get('headline'),
                json_ld.get('headline'),
                meta.get('open_graph', {}).get('og:title'),
                meta.get('title')
            ]),
            "author_url": self._get_reliable_value([
                combined.get('author', {}).get('url') if isinstance(combined.get('author'), dict) else None,
                json_ld.get('author', {}).get('url') if isinstance(json_ld.get('author'), dict) else None
            ]),
            "author_name": self._get_reliable_value([
                combined.get('author', {}).get('name') if isinstance(combined.get('author'), dict) else None,
                json_ld.get('author', {}).get('name') if isinstance(json_ld.get('author'), dict) else None
            ]),
            "full_name": self._get_reliable_value([
                combined.get('author', {}).get('name') if isinstance(combined.get('author'), dict) else None,
                json_ld.get('author', {}).get('name') if isinstance(json_ld.get('author'), dict) else None
            ]),
            "comment_count": self._get_reliable_value([
                combined.get('comment_count'),
                combined.get('comments_count'),
                json_ld.get('comment_count')
            ], convert_to_int=True),
            "likes_count": self._get_reliable_value([
                combined.get('likes'),
                json_ld.get('likes')
            ], convert_to_int=True),
            "followers": self._get_reliable_value([
                combined.get('author_followers'),
                json_ld.get('author_followers')
            ], convert_to_int=True),
            "date_published": self._get_reliable_value([
                combined.get('date_published'),
                json_ld.get('date_published')
            ])
        }
    
    def _structure_newsletter_data(self, combined: Dict, json_ld: Dict, meta: Dict, url: str) -> Dict[str, Any]:
        """Structure newsletter data"""
        
        # Extract username from URL
        username_match = re.search(r'linkedin\.com/newsletters/([^/?]+)', url)
        username = username_match.group(1) if username_match else ""
        
        return {
            "username": username,
            "full_name": self._get_reliable_value([
                combined.get('name'),
                json_ld.get('name'),
                meta.get('open_graph', {}).get('og:title', '').split(' | ')[0] if ' | ' in meta.get('open_graph', {}).get('og:title', '') else meta.get('open_graph', {}).get('og:title'),
                meta.get('title', '').split(' | ')[0] if ' | ' in meta.get('title', '') else meta.get('title')
            ]),
            "description": self._get_reliable_value([
                combined.get('description'),
                json_ld.get('description'),
                meta.get('open_graph', {}).get('og:description'),
                meta.get('description')
            ]),
            "author_name": self._get_reliable_value([
                combined.get('name'),
                json_ld.get('name'),
                meta.get('open_graph', {}).get('og:title', '').split(' | ')[0] if ' | ' in meta.get('open_graph', {}).get('og:title', '') else meta.get('open_graph', {}).get('og:title'),
                meta.get('title', '').split(' | ')[0] if ' | ' in meta.get('title', '') else meta.get('title')
            ]),
            "date_published": self._get_reliable_value([
                combined.get('date_published'),
                json_ld.get('date_published')
            ])
        }
    
    def _structure_generic_data(self, combined: Dict, json_ld: Dict, meta: Dict, url: str) -> Dict[str, Any]:
        """Structure generic data for unknown URL types"""
        
        return {
            "full_name": self._get_reliable_value([
                combined.get('name'),
                json_ld.get('name'),
                meta.get('open_graph', {}).get('og:title'),
                meta.get('title')
            ]),
            "description": self._get_reliable_value([
                combined.get('description'),
                json_ld.get('description'),
                meta.get('open_graph', {}).get('og:description'),
                meta.get('description')
            ]),
            "url": url,
            "image_url": self._get_reliable_value([
                combined.get('image_url'),
                json_ld.get('image_url'),
                meta.get('open_graph', {}).get('og:image')
            ])
        }
    
    def _get_reliable_value(self, values: List[Any], convert_to_int: bool = False) -> Any:
        """Get the most reliable non-empty value from a list"""
        
        for value in values:
            if value is not None and value != '' and value != 'N/A':
                if convert_to_int:
                    try:
                        if isinstance(value, str):
                            # Remove commas and convert
                            clean_value = value.replace(',', '').replace(' ', '')
                            return int(clean_value)
                        elif isinstance(value, (int, float)):
                            return int(value)
                    except (ValueError, TypeError):
                        continue
                else:
                    return value
        
        return None if not convert_to_int else 0
    
    def _extract_title_from_meta(self, meta: Dict) -> Optional[str]:
        """Extract job title from meta data"""
        
        og_title = meta.get('open_graph', {}).get('og:title', '')
        if ' | ' in og_title:
            parts = og_title.split(' | ')
            if len(parts) > 1:
                return parts[1]  # Usually job title comes after name
        
        return None
    
    def _format_company_address(self, address_dict: Dict) -> str:
        """Format company address from dictionary"""
        
        if not address_dict:
            return ""
        
        address_parts = []
        
        if address_dict.get('street'):
            address_parts.append(address_dict['street'])
        if address_dict.get('city'):
            address_parts.append(address_dict['city'])
        if address_dict.get('region'):
            address_parts.append(address_dict['region'])
        if address_dict.get('postal_code'):
            address_parts.append(address_dict['postal_code'])
        if address_dict.get('country'):
            address_parts.append(address_dict['country'])
        
        return ', '.join(address_parts) if address_parts else ""
    
    def _has_meaningful_data(self, structured: Dict[str, Any]) -> bool:
        """Check if structured data has meaningful content"""
        
        # Must have at least a name or title
        key_fields = ['full_name', 'name', 'headline', 'title']
        
        for field in key_fields:
            if structured.get(field) and structured[field].strip():
                return True
        
        return False
    
    def _save_results_to_file(self, results: Dict[str, Any], filename: str) -> None:
        """Save results to JSON file"""
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n💾 Results saved to: {filename}")
            print(f"   File size: {len(json.dumps(results, indent=2, ensure_ascii=False, default=str)):,} characters")
        
        except Exception as e:
            print(f"❌ Error saving results to {filename}: {e}")
    
    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print scraping summary"""
        
        metadata = results.get("scraping_metadata", {})
        successful = metadata.get("successful_scrapes", 0)
        failed = metadata.get("failed_scrapes", 0)
        total = metadata.get("total_urls", 0)
        
        print(f"\n{'='*80}")
        print("🎯 LINKEDIN SCRAPING SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successful: {successful}/{total} ({successful/total*100 if total > 0 else 0:.1f}%)")
        print(f"❌ Failed: {failed}/{total} ({failed/total*100 if total > 0 else 0:.1f}%)")
        
        if results.get("scraped_data"):
            print(f"\n📊 Successfully scraped:")
            for item in results["scraped_data"]:
                name = item.get('full_name', 'Unknown')
                url_type = item.get('url_type', 'unknown')
                print(f"  ✓ {name} ({url_type})")
        
        if results.get("failed_urls"):
            print(f"\n❌ Failed URLs:")
            for item in results["failed_urls"]:
                print(f"  ✗ {item['url']}: {item['error']}")
        
        print(f"{'='*80}")


# Global instance
_scraper_instance = None


def linkedin_scraper(urls: List[str], output_filename: str = "linkedin_scraped_data.json", headless: bool = True) -> Dict[str, Any]:
    """
    Simple one-line LinkedIn scraper function
    
    Args:
        urls: List of LinkedIn URLs to scrape
        output_filename: Name of output JSON file (default: "linkedin_scraped_data.json")
        headless: Run browser in headless mode (default: True)
    
    Returns:
        Dict containing scraped data and metadata
    
    Usage:
        from main import linkedin_scraper
        
        urls = [
            "https://www.linkedin.com/in/williamhgates/",
            "https://www.linkedin.com/company/microsoft/"
        ]
        
        results = linkedin_scraper(urls)
    """
    
    global _scraper_instance
    
    if not urls:
        print("❌ No URLs provided")
        return {"error": "No URLs provided"}
    
    try:
        # Create scraper instance
        _scraper_instance = LinkedInScraperMain(headless=headless, enable_anti_detection=True)
        
        # Run async scraping
        results = asyncio.run(_scraper_instance.scrape_async(urls, output_filename))
        
        return results
    
    except Exception as e:
        print(f"❌ LinkedIn scraper failed: {e}")
        return {"error": str(e)}


# Alternative class-based approach (if preferred)
class LinkedInScraper:
    """Alternative class-based interface"""
    
    def __init__(self, headless: bool = True):
        self.scraper = LinkedInScraperMain(headless=headless, enable_anti_detection=True)
    
    def scrape(self, urls: List[str], output_filename: str = "linkedin_scraped_data.json") -> Dict[str, Any]:
        """
        Scrape LinkedIn URLs
        
        Usage:
            from main import LinkedInScraper
            
            scraper = LinkedInScraper()
            results = scraper.scrape(urls)
        """
        
        if not urls:
            print("❌ No URLs provided")
            return {"error": "No URLs provided"}
        
        try:
            return asyncio.run(self.scraper.scrape_async(urls, output_filename))
        except Exception as e:
            print(f"❌ LinkedIn scraper failed: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    # Example usage
    test_urls = [
        "https://www.linkedin.com/in/williamhgates/",
        "https://www.linkedin.com/company/microsoft/",
        "https://www.linkedin.com/posts/aiqod_inside-aiqod-how-were-building-enterprise-ready-activity-7348224698146541568-N7oQ",
        "https://www.linkedin.com/newsletters/aiqod-insider-7325820451622940672"
    ]
    # test_urls = [
    #     "https://www.linkedin.com/company/microsoft/"
    # ]
    print("Testing LinkedIn Scraper...")
    print("Method 1: Function approach")
    results = linkedin_scraper(test_urls, "test_results.json", headless=False)
    
    # print("\nMethod 2: Class approach")
    # scraper = LinkedInScraper(headless=False)
    # results2 = scraper.scrape(test_urls, "test_results_class.json")