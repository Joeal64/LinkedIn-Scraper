import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os
import sys
from datetime import datetime

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

def get_job_ids(title, location, start=0):
    """
    Retrieve job IDs from LinkedIn search results.
    """
    # Construct the URL for LinkedIn job search
    title_encoded = title.replace(' ', '%20')
    location_encoded = location.replace(' ', '%20')
    list_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={title_encoded}&location={location_encoded}&start={start}"
    
    print(f"Searching URL: {list_url}")
    
    try:
        # Send a GET request to the URL
        response = requests.get(list_url, headers=get_headers())
        
        # Print status code and first 100 chars of response
        print(f"Response status: {response.status_code}")
        print(f"Response preview: {response.text[:100].strip()}")
        
        response.raise_for_status()  # Raise an error for bad status codes
        
        # Parse the response and find all list items (job postings)
        list_soup = BeautifulSoup(response.text, "html.parser")
        page_jobs = list_soup.find_all("li")
        print(f"Found {len(page_jobs)} job listings on page")
        
        # Extract job IDs
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
    # Add random delay to avoid rate limiting
    actual_delay = delay + random.uniform(-5, 5)  # 10-20 second delay
    print(f"Waiting {actual_delay:.1f} seconds before next request...")
    time.sleep(actual_delay)
    
    # Construct the URL for the job posting
    job_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    
    try:
        # Send a GET request to the job URL
        job_response = requests.get(job_url, headers=get_headers())
        print(f"Response status: {job_response.status_code}")
        
        # If we get a non-200 status, try waiting longer and retrying once
        if job_response.status_code != 200:
            print("Non-200 status, waiting longer and retrying...")
            time.sleep(60)  # Wait a full minute
            job_response = requests.get(job_url, headers=get_headers())
            print(f"Retry response status: {job_response.status_code}")
        
        job_response.raise_for_status()
        
        # Parse the response
        job_soup = BeautifulSoup(job_response.text, "html.parser")
        
        # Create a dictionary to store job details
        job_post = {
            "job_id": job_id,
            "job_title": None,
            "company_name": None,
            "time_posted": None,
            "num_applicants": None,
            "location": None,
        }
        
        # Extract job title (try different possible class names)
        try:
            title_elem = job_soup.find("h2", class_=lambda c: c and "top-card-layout__title" in c)
            if not title_elem:
                title_elem = job_soup.find("h2", class_=lambda c: c and "title" in c)
            if title_elem:
                job_post["job_title"] = title_elem.text.strip()
                print(f"Found job title: {job_post['job_title']}")
        except Exception as e:
            print(f"Error extracting job title: {e}")
        
        # Extract company name (try different possible elements)
        try:
            company_elem = job_soup.find("a", class_=lambda c: c and "topcard__org-name-link" in c)
            if not company_elem:
                company_elem = job_soup.find("span", class_=lambda c: c and "company-name" in c)
            if company_elem:
                job_post["company_name"] = company_elem.text.strip()
        except Exception as e:
            print(f"Error extracting company name: {e}")
        
        # Extract location
        try:
            location_elem = job_soup.find("span", class_=lambda c: c and "location" in c)
            if location_elem:
                job_post["location"] = location_elem.text.strip()
        except Exception as e:
            print(f"Error extracting location: {e}")
        
        # Extract time posted
        try:
            time_elem = job_soup.find("span", class_=lambda c: c and "posted-time" in c)
            if time_elem:
                job_post["time_posted"] = time_elem.text.strip()
        except Exception as e:
            print(f"Error extracting time posted: {e}")
        
        # Extract number of applicants
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
    Main function to scrape LinkedIn jobs.
    """
    print(f"Searching for '{title}' jobs in '{location}'")
    
    # Get job IDs
    job_ids = get_job_ids(title, location, start)
    print(f"Found {len(job_ids)} job IDs")
    
    if not job_ids:
        print("No jobs found! The search might be blocked or returned no results.")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            "job_id", "job_title", "company_name", "location", 
            "time_posted", "num_applicants", "error"
        ])
    
    # Limit the number of jobs to scrape
    job_ids = job_ids[:max_jobs]
    print(f"Will process {len(job_ids)} jobs")
    
    # Get job details
    job_list = []
    for i, job_id in enumerate(job_ids):
        print(f"Processing job {i+1}/{len(job_ids)}: {job_id}")
        job_details = get_job_details(job_id)
        job_list.append(job_details)
    
    # Create DataFrame
    jobs_df = pd.DataFrame(job_list)
    print(f"Scraped {len(jobs_df)} jobs successfully")
    
    return jobs_df

def main():
    """
    Main execution function.
    """
    # Create a timestamped folder for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(os.getcwd(), f"LinkedInJobs_{timestamp}")
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Files will be saved to: {save_dir}")
    
    # Set parameters
    job_titles = ["Software Intern", "Software Engineering Intern", "Data Analyst Intern"]
    job_location = "Ireland"
    
    # Create a log file
    log_file = os.path.join(save_dir, "scraper_log.txt")
    
    # Redirect stdout to both console and log file
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
    print(f"Searching for {len(job_titles)} job titles in {job_location}")
    
    # Process each job title
    all_jobs = []
    
    for job_title in job_titles:
        print(f"\n===== SEARCHING FOR: {job_title} =====\n")
        
        # Create filename based on job title
        file_name = f"{job_title.replace(' ', '_')}_{job_location.replace(' ', '_')}.csv"
        output_file = os.path.join(save_dir, file_name)
        
        # Run the scraper
        df = scrape_linkedin_jobs(job_title, job_location)
        
        # Check if we got any results
        if df.empty:
            print(f"No results found for {job_title}")
            continue
        
        # Print preview of the data
        print("\nData preview:")
        print(df.head(2))
        
        # Save individual file
        try:
            df.to_csv(output_file, index=False)
            print(f"Data saved to {output_file}")
        except Exception as e:
            print(f"Error saving data to {output_file}: {e}")
        
        # Add to combined dataset
        df['search_query'] = job_title  # Add column to track which search produced these results
        all_jobs.append(df)
    
    # Create combined dataset
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