import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
import sys
from datetime import datetime
import json

# Configure request headers to look more like a browser
def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.linkedin.com/",
        "Cache-Control": "max-age=0"
    }

def call_openai_api(user_message, api_key):
    """
    Call OpenAI API to parse user intent using GPT.
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    system_prompt = """You are a job search assistant. Extract the job title and location from the user's query.
    Return ONLY a valid JSON object with keys "job_title" and "location". Nothing else.

    Rules:
    - Expand abbreviations BUT keep seniority/type qualifiers intact
    - "SWE intern" -> "software engineer intern" (NOT "software engineer")
    - "ML engineer" -> "machine learning engineer"
    - ALWAYS preserve: intern, internship, junior, senior, lead, staff, principal, graduate, entry-level, trainee
    - Keep locations as provided (city, country, or region)
    - If no location is specified, use "Remote"

    Examples:
    User: "find me software engineering jobs in Dublin"
    Response: {"job_title": "software engineer", "location": "Dublin"}

    User: "SWE intern jobs in dublin"
    Response: {"job_title": "software engineer intern", "location": "Dublin"}

    User: "I'm looking for data scientist positions in London"
    Response: {"job_title": "data scientist", "location": "London"}

    User: "junior python developer roles around San Francisco"
    Response: {"job_title": "junior python developer", "location": "San Francisco"}

    User: "marketing internships in Ireland"
    Response: {"job_title": "marketing intern", "location": "Ireland"}

    User: "remote react developer jobs"
    Response: {"job_title": "react developer", "location": "Remote"}"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2,
        "max_tokens": 150,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        ai_response = result['choices'][0]['message']['content'].strip()
        print(f"🤖 AI Response: {ai_response}")

        # Parse JSON
        parsed = json.loads(ai_response)
        job_title = parsed.get('job_title', '').strip()
        location = parsed.get('location', '').strip()

        if not job_title or not location:
            print(f"⚠️  Incomplete data: job_title='{job_title}', location='{location}'")
            return None, None

        return job_title, location

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"❌ Authentication failed. Please check your API key.")
        elif e.response.status_code == 429:
            print(f"❌ Rate limit exceeded. Please try again later.")
        else:
            print(f"❌ HTTP Error: {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse AI response as JSON: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Error calling OpenAI API: {e}")
        return None, None

def call_ollama_api(user_message):
    """
    Call local Ollama API (free, runs on your machine).
    """
    url = "http://localhost:11434/api/generate"

    system_prompt = """You are a job search assistant. Extract the job title and location from the user's query.
    Return ONLY a valid JSON object with keys "job_title" and "location". Nothing else.

    Rules:
    - Expand abbreviations BUT keep seniority/type qualifiers intact
    - "SWE intern" -> "software engineer intern" (NOT "software engineer")
    - "ML engineer" -> "machine learning engineer"
    - ALWAYS preserve: intern, internship, junior, senior, lead, staff, principal, graduate, entry-level, trainee
    - Keep locations as provided (city, country, or region)
    - If no location is specified, use "Remote"

    Examples:
    User: "find me software engineering jobs in Dublin"
    Response: {"job_title": "software engineer", "location": "Dublin"}

    User: "SWE intern jobs in dublin"
    Response: {"job_title": "software engineer intern", "location": "Dublin"}

    User: "I'm looking for data scientist positions in London"
    Response: {"job_title": "data scientist", "location": "London"}

    User: "junior python developer in SF"
    Response: {"job_title": "junior python developer", "location": "San Francisco"}

    User: "marketing internships in Ireland"
    Response: {"job_title": "marketing intern", "location": "Ireland"}"""

    data = {
        "model": "llama3.2",
        "prompt": f"{system_prompt}\n\nUser: {user_message}\nResponse:",
        "stream": False,
        "format": "json"
    }

    try:
        print("🤖 Contacting Ollama AI...")
        response = requests.post(url, json=data, timeout=90)
        response.raise_for_status()
        result = response.json()

        ai_response = result['response'].strip()
        print(f"🤖 AI Response: {ai_response}")

        # Extract JSON from response
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            json_str = ai_response[json_start:json_end]
            parsed = json.loads(json_str)
            job_title = parsed.get('job_title', '').strip()
            location = parsed.get('location', '').strip()

            if not job_title or not location:
                print(f"⚠️  Incomplete data: job_title='{job_title}', location='{location}'")
                return None, None

            return job_title, location
        else:
            print("❌ Could not find valid JSON in response")
            return None, None

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Ollama. Make sure it's running:")
        print("   Run: ollama serve")
        print("   Also ensure you have llama3.2 installed: ollama pull llama3.2")
        return None, None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse AI response as JSON: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Error calling Ollama API: {e}")
        return None, None

def call_claude_api(user_message, api_key):
    """
    Call Anthropic Claude API to parse user intent.
    """
    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }

    system_prompt = """You are a job search assistant. Extract the job title and location from the user's query.
    Return ONLY a valid JSON object with keys "job_title" and "location". Nothing else.

    Rules:
    - Expand abbreviations BUT keep seniority/type qualifiers intact
    - "SWE intern" -> "software engineer intern" (NOT "software engineer")
    - "ML engineer" -> "machine learning engineer"
    - ALWAYS preserve: intern, internship, junior, senior, lead, staff, principal, graduate, entry-level, trainee
    - Keep locations as provided (city, country, or region)
    - If no location is specified, use "Remote"

    Examples:
    User: "find me software engineering jobs in Dublin"
    Response: {"job_title": "software engineer", "location": "Dublin"}

    User: "SWE intern jobs in dublin"
    Response: {"job_title": "software engineer intern", "location": "Dublin"}

    User: "I'm looking for data scientist positions in London"
    Response: {"job_title": "data scientist", "location": "London"}

    User: "senior ML roles in NYC"
    Response: {"job_title": "senior machine learning engineer", "location": "New York City"}

    User: "marketing internships in Ireland"
    Response: {"job_title": "marketing intern", "location": "Ireland"}"""

    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 150,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        ai_response = result['content'][0]['text'].strip()
        print(f"🤖 AI Response: {ai_response}")

        # Extract JSON from response
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            json_str = ai_response[json_start:json_end]
            parsed = json.loads(json_str)
            job_title = parsed.get('job_title', '').strip()
            location = parsed.get('location', '').strip()

            if not job_title or not location:
                print(f"⚠️  Incomplete data: job_title='{job_title}', location='{location}'")
                return None, None

            return job_title, location
        else:
            print("❌ Could not find valid JSON in response")
            return None, None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"❌ Authentication failed. Please check your API key.")
        elif e.response.status_code == 429:
            print(f"❌ Rate limit exceeded. Please try again later.")
        else:
            print(f"❌ HTTP Error: {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse AI response as JSON: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Error calling Claude API: {e}")
        return None, None

def get_job_ids(title, location, start=0):
    """
    Retrieve job IDs from LinkedIn search results.
    """
    title_encoded = title.replace(' ', '%20')
    location_encoded = location.replace(' ', '%20')
    list_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={title_encoded}&location={location_encoded}&start={start}"
    
    print(f"Searching URL: {list_url}")
    
    try:
        response = requests.get(list_url, headers=get_headers())
        
        print(f"Response status: {response.status_code}")
        print(f"Response preview: {response.text[:100].strip()}")
        
        response.raise_for_status()
        
        list_soup = BeautifulSoup(response.text, "html.parser")
        page_jobs = list_soup.find_all("li")
        print(f"Found {len(page_jobs)} job listings on page")
        
        id_list = []
        for job in page_jobs:
            try:
                base_card_div = job.find("div", {"class": "base-card"})
                if base_card_div and base_card_div.get("data-entity-urn"):
                    job_id = base_card_div.get("data-entity-urn").split(":")[3]
                    id_list.append(job_id)
                    print(f"Found job ID: {job_id}")
            except Exception as e:
                print(f"Error extracting job ID: {e}")
        
        return id_list
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching job listings: {e}")
        return []

def get_job_details(job_id, delay=15):
    """
    Retrieve detailed information for a specific job posting.
    """
    actual_delay = delay + random.uniform(-5, 5)
    print(f"Waiting {actual_delay:.1f} seconds before next request...")
    time.sleep(actual_delay)
    
    job_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    
    try:
        job_response = requests.get(job_url, headers=get_headers())
        print(f"Response status: {job_response.status_code}")
        
        if job_response.status_code != 200:
            print("Non-200 status, waiting longer and retrying...")
            time.sleep(60)
            job_response = requests.get(job_url, headers=get_headers())
            print(f"Retry response status: {job_response.status_code}")
        
        job_response.raise_for_status()
        
        job_soup = BeautifulSoup(job_response.text, "html.parser")
        
        job_post = {
            "job_id": job_id,
            "job_title": None,
            "company_name": None,
            "time_posted": None,
            "num_applicants": None,
            "location": None,
        }
        
        try:
            title_elem = job_soup.find("h2", class_=lambda c: c and "top-card-layout__title" in c)
            if not title_elem:
                title_elem = job_soup.find("h2", class_=lambda c: c and "title" in c)
            if title_elem:
                job_post["job_title"] = title_elem.text.strip()
                print(f"Found job title: {job_post['job_title']}")
        except Exception as e:
            print(f"Error extracting job title: {e}")
        
        try:
            company_elem = job_soup.find("a", class_=lambda c: c and "topcard__org-name-link" in c)
            if not company_elem:
                company_elem = job_soup.find("span", class_=lambda c: c and "company-name" in c)
            if company_elem:
                job_post["company_name"] = company_elem.text.strip()
        except Exception as e:
            print(f"Error extracting company name: {e}")
        
        try:
            location_elem = job_soup.find("span", class_=lambda c: c and "location" in c)
            if location_elem:
                job_post["location"] = location_elem.text.strip()
        except Exception as e:
            print(f"Error extracting location: {e}")
        
        try:
            time_elem = job_soup.find("span", class_=lambda c: c and "posted-time" in c)
            if time_elem:
                job_post["time_posted"] = time_elem.text.strip()
        except Exception as e:
            print(f"Error extracting time posted: {e}")
        
        try:
            applicants_elem = job_soup.find("span", class_=lambda c: c and "num-applicants" in c)
            if applicants_elem:
                job_post["num_applicants"] = applicants_elem.text.strip()
        except Exception as e:
            print(f"Error extracting number of applicants: {e}")
        
        return job_post
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching job details for job ID {job_id}: {e}")
        return {"job_id": job_id, "error": str(e)}

def scrape_linkedin_jobs(title, location, start=0, max_jobs=10):
    """
    Main function to scrape LinkedIn jobs with progress indicators.
    """
    print(f"🔍 Searching for '{title}' jobs in '{location}'")

    job_ids = get_job_ids(title, location, start)
    print(f"📊 Found {len(job_ids)} job IDs")

    if not job_ids:
        print("⚠️  No jobs found! The search might be blocked or returned no results.")
        return pd.DataFrame(columns=[
            "job_id", "job_title", "company_name", "location",
            "time_posted", "num_applicants", "error"
        ])

    job_ids = job_ids[:max_jobs]
    print(f"📝 Will process {len(job_ids)} jobs\n")

    job_list = []
    for i, job_id in enumerate(job_ids):
        print(f"⏳ Processing job {i+1}/{len(job_ids)}: {job_id}")
        job_details = get_job_details(job_id)
        job_list.append(job_details)

        # Show mini progress
        if job_details.get('job_title'):
            print(f"   ✓ {job_details['job_title']} at {job_details.get('company_name', 'Unknown')}")
        else:
            print(f"   ⚠️ Could not extract full details")

    jobs_df = pd.DataFrame(job_list)
    successful = len(jobs_df[jobs_df['job_title'].notna()])
    print(f"\n✅ Scraped {successful}/{len(jobs_df)} jobs successfully")

    return jobs_df

def manual_input_fallback():
    """
    Fallback to manual input if AI fails.
    """
    print("\n📝 Let's enter the details manually:")
    job_title = input("   Job Title: ").strip()
    location = input("   Location: ").strip()

    if not job_title or not location:
        print("❌ Both job title and location are required.")
        return None, None

    return job_title, location

def ai_bot_mode():
    """
    Improved AI bot mode with better error handling and multiple providers.
    """
    print("=" * 60)
    print("🤖 LinkedIn Job Scraper AI Bot")
    print("=" * 60)
    print("\nChoose your AI provider:")
    print("1. OpenAI GPT-4o-mini (requires API key) - Fast & accurate")
    print("2. Claude 3.5 Haiku (requires API key) - Anthropic's model")
    print("3. Ollama (free, local) - Requires Ollama installed")
    print("4. Manual Mode (no AI) - Enter job details yourself")

    provider_choice = input("\nEnter choice (1/2/3/4): ").strip()

    ai_provider = None
    api_key = None

    if provider_choice == "1":
        ai_provider = "openai"
        api_key = input("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("❌ No API key provided. Cannot proceed.")
            return
        print("✅ OpenAI configured!")
    elif provider_choice == "2":
        ai_provider = "claude"
        api_key = input("Enter your Anthropic API key: ").strip()
        if not api_key:
            print("❌ No API key provided. Cannot proceed.")
            return
        print("✅ Claude configured!")
    elif provider_choice == "3":
        ai_provider = "ollama"
        print("\n⚠️  Make sure Ollama is running:")
        print("   1. Install from: https://ollama.com")
        print("   2. Run: ollama pull llama3.2")
        print("   3. Run: ollama serve")
        input("\nPress Enter when ready...")
    elif provider_choice == "4":
        ai_provider = "manual"
        print("✅ Manual mode selected!")
    else:
        print("❌ Invalid choice. Exiting.")
        return

    # Ask for settings
    print("\n" + "=" * 60)
    auto_confirm = input("Auto-confirm searches? (yes/no, default: no): ").strip().lower()
    auto_confirm = auto_confirm in ['yes', 'y']

    default_max_jobs = input("Default number of jobs to scrape? (default: 10): ").strip()
    default_max_jobs = int(default_max_jobs) if default_max_jobs.isdigit() else 10

    print("\n" + "=" * 60)
    print("I can help you find jobs on LinkedIn!")
    print("\nExamples:")
    print("  - 'find me software engineering jobs in Dublin'")
    print("  - 'data scientist positions in London'")
    print("  - 'marketing intern in San Francisco'")
    print("  - 'remote python developer'")
    print("\nType 'quit' or 'exit' to stop.\n")

    retry_count = 0
    max_retries = 2

    while True:
        user_query = input("👤 You: ").strip()

        if user_query.lower() in ['quit', 'exit', 'stop', 'bye']:
            print("👋 Goodbye!")
            break

        if not user_query:
            print("Please enter a job search query.\n")
            continue

        job_title = None
        location = None

        # Parse using AI or manual mode
        if ai_provider == "manual":
            job_title, location = manual_input_fallback()
            if not job_title or not location:
                continue
        else:
            print(f"\n🤖 Bot: Let me understand your request using AI...")

            # Call the appropriate AI provider
            if ai_provider == "openai":
                job_title, location = call_openai_api(user_query, api_key)
            elif ai_provider == "claude":
                job_title, location = call_claude_api(user_query, api_key)
            else:  # ollama
                job_title, location = call_ollama_api(user_query)

            if not job_title or not location:
                retry_count += 1
                print(f"❌ AI couldn't parse your query (Attempt {retry_count}/{max_retries}).")

                if retry_count >= max_retries:
                    print("\n⚠️  AI is having trouble. Would you like to enter details manually?")
                    manual_choice = input("   Use manual input? (yes/no): ").strip().lower()

                    if manual_choice in ['yes', 'y']:
                        job_title, location = manual_input_fallback()
                        retry_count = 0
                        if not job_title or not location:
                            continue
                    else:
                        print("   Example: 'software engineer jobs in Dublin'\n")
                        retry_count = 0
                        continue
                else:
                    print(f"   Example: 'software engineer jobs in Dublin'\n")
                    continue
            else:
                retry_count = 0

        print(f"\n✅ AI Understood! Searching for:")
        print(f"   📋 Job Title: {job_title}")
        print(f"   📍 Location: {location}")

        # Confirmation step (unless auto-confirm is enabled)
        if not auto_confirm:
            confirm = input("\n   Proceed? (yes/no/edit): ").strip().lower()

            if confirm in ['no', 'n']:
                print("Search cancelled.\n")
                continue
            elif confirm in ['edit', 'e']:
                job_title, location = manual_input_fallback()
                if not job_title or not location:
                    continue

        max_jobs_input = input(f"   How many jobs to scrape? (default {default_max_jobs}): ").strip()
        max_jobs = int(max_jobs_input) if max_jobs_input.isdigit() else default_max_jobs

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = os.path.join(os.getcwd(), f"LinkedInJobs_{timestamp}")
        os.makedirs(save_dir, exist_ok=True)

        print(f"\n🔍 Starting search...")
        print(f"📁 Results will be saved to: {save_dir}\n")

        df = scrape_linkedin_jobs(job_title, location, max_jobs=max_jobs)

        if df.empty:
            print("\n❌ No jobs found!")
            print("   This could mean:")
            print("   - LinkedIn is blocking requests (too many requests)")
            print("   - No jobs match your search criteria")
            print("   - Try a different location or job title\n")
        else:
            print(f"\n✅ Found {len(df)} jobs!")
            print("\nPreview of results:")
            print("=" * 60)
            for idx, row in df.head(5).iterrows():
                print(f"\n{idx+1}. {row['job_title'] or 'N/A'}")
                print(f"   Company: {row['company_name'] or 'N/A'}")
                print(f"   Location: {row['location'] or 'N/A'}")
                print(f"   Posted: {row['time_posted'] or 'N/A'}")

            if len(df) > 5:
                print(f"\n... and {len(df) - 5} more jobs")

            file_name = f"{job_title.replace(' ', '_')}_{location.replace(' ', '_')}.csv"
            output_file = os.path.join(save_dir, file_name)
            df.to_csv(output_file, index=False)
            print(f"\n💾 Data saved to: {output_file}")

        print("\n" + "=" * 60 + "\n")

def main():
    """
    Main execution function.
    """
    print("\nSelect mode:")
    print("1. AI Bot Mode (Interactive with REAL AI)")
    print("2. Batch Mode (Original functionality)")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == "1":
        ai_bot_mode()
    else:
        batch_mode()

def batch_mode():
    """
    Original batch scraping functionality.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(os.getcwd(), f"LinkedInJobs_{timestamp}")
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Files will be saved to: {save_dir}")
    
    job_titles = ["Software Intern", "Software Engineering Intern", "Software Developer Intern","Software Development Intern","IT Intern","Machine Learning Intern","Cybersecurity Intern"]
    job_locations = ["Ireland", "United Kingdom"]
    
    log_file = os.path.join(save_dir, "scraper_log.txt")
    
    class Logger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "w")
        
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()
        
        def flush(self):
            self.terminal.flush()
            self.log.flush()
    
    sys.stdout = Logger(log_file)
    
    print(f"LinkedIn Job Scraper started at {datetime.now()}")
    print(f"Searching for {len(job_titles)} job titles in {len(job_locations)} locations")
    
    for job_location in job_locations:
        all_jobs = []
        for job_title in job_titles:
            print(f"\n===== SEARCHING FOR: {job_title} =====\n")
            
            file_name = f"{job_title.replace(' ', '_')}_{job_location.replace(' ', '_')}.csv"
            output_file = os.path.join(save_dir, file_name)
            
            df = scrape_linkedin_jobs(job_title, job_location)
            
            if df.empty:
                print(f"No results found for {job_title}")
                continue
            
            print("\nData preview:")
            print(df.head(2))
            
            try:
                df.to_csv(output_file, index=False)
                print(f"Data saved to {output_file}")
            except Exception as e:
                print(f"Error saving data to {output_file}: {e}")
            
            df['search_query'] = job_title
            all_jobs.append(df)
    
        if all_jobs:
            try:
                combined_df = pd.concat(all_jobs, ignore_index=True)
                combined_file = os.path.join(save_dir, f"All_{job_location}_Jobs.csv")
                combined_df.to_csv(combined_file, index=False)
                print(f"\nCombined data saved to {combined_file}")
            except Exception as e:
                print(f"Error creating combined file: {e}")
        else:
            print("\nNo data collected for any job title!")
        
    print(f"\nAll operations completed at {datetime.now()}")

if __name__ == "__main__":
    main()