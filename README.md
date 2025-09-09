# LinkedIn Job Scraper

A Python tool that scrapes job listings from LinkedIn based on job titles and locations.

## Features

- Search multiple job titles in one run
- Extract job details (title, company, location, posting time, applicants)
- Built-in rate limiting to avoid being blocked
- Automatic CSV export with timestamped folders
- Detailed logging for troubleshooting

## Installation

```bash
pip install requests beautifulsoup4 pandas
```

## Usage

1. **Edit search parameters** in `LinkScrape.py`:
   ```python
   job_titles = ["Software Engineer", "Data Analyst", "Product Manager"]
   job_location = "New York"
   ```

2. **Run the scraper**:
   ```bash
   python LinkScrape.py
   ```

3. **Find results** in the generated `LinkedInJobs_[timestamp]` folder

## Output

- Individual CSV files for each job search
- Combined CSV with all results
- Execution log file

## Configuration

**Adjust job count**: Change `max_jobs` in the `scrape_linkedin_jobs()` function
**Modify delays**: Edit `delay` parameter to increase/decrease request intervals
**Add job titles**: Extend the `job_titles` list in `main()`

## Data Fields

Each CSV contains: `job_id`, `job_title`, `company_name`, `location`, `time_posted`, `num_applicants`

## Important Notes

- For educational purposes only
- Includes delays to respect LinkedIn's servers
- Check LinkedIn's Terms of Service before use
- Monitor log files if issues occur

## Troubleshooting

- **No results**: Try different search terms or increase delays
- **Errors**: Check `scraper_log.txt` for details
- **Rate limits**: Wait longer between requests 
