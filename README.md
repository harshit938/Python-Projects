# 🐍 Python Projects — Web Scraping, Automation & Data Analysis

> Production-ready Python scripts built during my 9-month Data & Automation Apprenticeship at **AdGlobal360 Pvt. Ltd.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-Scraping-green)](https://pypi.org/project/beautifulsoup4/)
[![Selenium](https://img.shields.io/badge/Selenium-Automation-orange)](https://selenium.dev)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-yellow)](https://pandas.pydata.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 📁 Projects Overview

| Project | Tech Stack | Output |
|---|---|---|
| [Amazon Product Price Scraper](#1-amazon-product-price-scraper) | BeautifulSoup, Requests, Pandas | CSV |
| [Automated Job Listings Scraper](#2-automated-job-listings-scraper) | Selenium, BeautifulSoup, Pandas | JSON + Excel |
| [Student Result Analysis System](#3-student-result-analysis-system) | Pandas, Matplotlib | CSV + Charts |

---

## 1. Amazon Product Price Scraper

**`AmazonScraper.py`**

Scrapes product names, prices, ratings, and review counts from Amazon India for any search keyword across multiple pages.

### Features
- Multi-page scraping with automatic pagination
- Rotating User-Agent headers to avoid IP blocking
- Retry logic with exponential back-off (3 attempts per page)
- CAPTCHA detection with graceful exit
- Structured CSV export with timestamp
- Full logging to file + console

### Tech Stack
`Python` `BeautifulSoup4` `Requests` `Pandas` `CSV`

### How to Run
```bash
pip install requests beautifulsoup4 pandas
python AmazonScraper.py
```

### Output Sample
```
=======================================================
  Keyword       : wireless earphones
  Total scraped : 48
  Avg Price     : ₹1,249
  Cheapest      : ₹399
  Most Expensive: ₹4,999
=======================================================
```

---

## 2. Automated Job Listings Scraper

**`JobScraper.py`**

Scrapes job titles, companies, locations, salaries, and descriptions from Naukri.com — a dynamic JavaScript-rendered portal — with auto-scheduled daily runs.

### Features
- Selenium WebDriver with headless Chrome (anti-detection configured)
- Handles infinite scroll, JS-rendered pages, and login flows
- BeautifulSoup for fast HTML parsing after Selenium renders the page
- Exports to both JSON and Excel
- Daily auto-scheduling via Python `schedule` library
- Robust error handling, retry logic, and structured logging

### Tech Stack
`Python` `Selenium` `BeautifulSoup4` `Pandas` `JSON` `openpyxl` `schedule`

### How to Run
```bash
pip install selenium beautifulsoup4 pandas openpyxl schedule
python JobScraper.py
```

> **Note:** Requires Google Chrome installed. ChromeDriver is managed automatically by Selenium 4+.

### Output Sample
```
=======================================================
  Total jobs scraped  : 87
  Unique companies    : 62
  Unique locations    : 14
=======================================================
```

---

## 3. Student Result Analysis System

**`StudentAnalysis.py`**

Reads student marks from a CSV file and generates comprehensive performance reports, grade assignments, and visualisations.

### Features
- Auto-generates sample data if no CSV is provided (great for demo)
- Subject-wise pass/fail analysis with configurable pass marks
- Grade assignment: A+ / A / B / C / D / F
- Class rank, topper, and lowest scorer detection
- 4 Matplotlib charts: subject averages, grade distribution pie, top 5 bar, pass vs fail per subject
- Saves student report, subject report, and pass/fail matrix to CSV

### Tech Stack
`Python` `Pandas` `NumPy` `Matplotlib` `CSV`

### How to Run
```bash
pip install pandas numpy matplotlib openpyxl
python StudentAnalysis.py
```

> To use your own data, place a `students.csv` file in the same folder with columns:
> `Roll No`, `Student Name`, `Subject1`, `Subject2`, ...

### Output Sample
```
============================================================
  STUDENT RESULT ANALYSIS — SUMMARY REPORT
============================================================
  Total Students   : 20
  Overall Passed   : 17  (85.0%)
  Overall Failed   : 3   (15.0%)
  Class Average    : 72.45 / 100
============================================================
  🏆 Topper        : Aarav Sharma  (Avg: 91.4, Grade: A+)
  📉 Lowest Scorer : Sahil Khan    (Avg: 48.2, Grade: D)
============================================================
```

---

## ⚙️ Installation (All Projects)

```bash
# Clone the repository
git clone https://github.com/harshit938/Python-Projects.git
cd Python-Projects

# Install all dependencies at once
pip install -r requirements.txt
```

---

## 📂 Project Structure

```
Python-Projects/
├── AmazonScraper.py        # Amazon product price scraper
├── JobScraper.py           # Naukri.com job listings scraper
├── StudentAnalysis.py      # Student result analysis system
├── requirements.txt        # All dependencies
├── .gitignore              # Ignored files
└── README.md               # This file
```

---

## 👤 Author

**Harshit Kumar Mishra**
- 📧 harshitkumarmishra32@gmail.com
- 💼 [LinkedIn](https://linkedin.com/in/harshitkumarmishra)
- 🐙 [GitHub](https://github.com/harshit938)

---

## 📄 License

This project is licensed under the MIT License.
