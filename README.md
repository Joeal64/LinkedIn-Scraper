# LinkedIn-Scraper


A Python tool that collects job listings from LinkedIn based on keywords and locations.

## Setup

1. Install required packages:
```
pip install requests beautifulsoup4 pandas
```

2. Save the LinkScrape.py file to your computer

## Usage

1. Edit the job titles and location in the code:
```python
job_titles = ["Software Intern", "Software Engineering Intern", "Data Analyst Intern"]
job_location = "Ireland"
```

2. Run the script:
```
python LinkScrape.py
```

3. Results are saved to a folder named `LinkedInJobs_[timestamp]`

## Output Files

- Individual CSV files for each job search
- Combined CSV with all results
- Log file with execution details

## Customization

To modify the script behavior:

- Change `max_jobs` value to collect more/fewer jobs
- Adjust the delay between requests (default 15 seconds)
- Add different job titles or locations


This tool is for educational purposes only. 
