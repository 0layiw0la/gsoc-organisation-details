from bs4 import BeautifulSoup
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import chromedriver_autoinstaller  
from fake_useragent import UserAgent

def get_org_links():
    """
    Extracts links to the individual pages of organizations listed in the Google Summer of Code (GSoC) 2025 program.
    """
    href_list = []
    driver_path = chromedriver_autoinstaller.install()
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment to enable headless mode.
    ua = UserAgent()
    options.add_argument(f"user-agent={ua.random}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(driver_path, options=options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://summerofcode.withgoogle.com/programs/2025/organizations")  # Change the URL for different years.
        time.sleep(2)

        # Scroll down to ensure elements are visible, adjust if necessary.
        for _ in range(1):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)


        # Switch from card view to list view.
        button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="mat-button-toggle-6-button"]')))
        button.click()
        time.sleep(2)

        # Scroll to the bottom of the page to load all elements.
        for _ in range(10):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

        # Open dropdown to adjust the number of items per page.
        bt2 = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="mat-select-value-3"]')))
        bt2.click()

        # Select 100 items per page.
        bt3 = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="mat-option-7"]')))
        bt3.click()

        time.sleep(1)

        # Find all organization elements and extract their links.
        orgs = driver.find_elements(By.TAG_NAME, "app-org-list")
        for org in orgs:
            try:
                link_element = org.find_element(By.TAG_NAME, "a")
                href = link_element.get_attribute("href")
                href_list.append(href)
            except Exception:
                pass

        # Scroll down again to ensure all elements are loaded.
        for _ in range(10):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

        # Click the "Next Page" button.
        bt4 = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/app-root/app-layout/mat-sidenav-container/mat-sidenav-content[1]/div/div/main/app-program-organizations/app-orgs-grid/section[2]/div/mat-paginator/div/div/div[2]/button[2]')))
        bt4.click()

        # Scroll up slightly to ensure visibility of new elements.
        driver.execute_script("window.scrollBy(0, -500);")
        time.sleep(1)

        # Extract organization links from the next page.
        orgs2 = driver.find_elements(By.TAG_NAME, "app-org-list")
        for org in orgs2:
            try:
                link_element = org.find_element(By.TAG_NAME, "a")
                href = link_element.get_attribute("href")
                href_list.append(href)
            except Exception:
                pass

    except Exception as e:
        print("Error:", e)
    finally:
        driver.quit()

    return href_list




def scrape_org_details(href_list):
    """
    Scrapes organization details (name and technologies used) from the GSoC 2025 organization pages.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    org_data = {}
    count = 0

    for url in href_list:
        try:
            driver.get(url)
            time.sleep(1)  # Allow time for the page to load

            # Extract the organization's name
            name_xpath = "/html/body/app-root/app-layout/mat-sidenav-container/mat-sidenav-content[1]/div/div/main/app-program-organization/app-org-page-title/app-feature-banner/section/div/div/app-feature-cta/div/div[1]/div[1]/h2/span"
            name = wait.until(EC.presence_of_element_located((By.XPATH, name_xpath))).text.strip()

            # Extract the list of technologies used
            tech_xpath = "/html/body/app-root/app-layout/mat-sidenav-container/mat-sidenav-content[1]/div/div/main/app-program-organization/app-org-info/section/div[2]/div/div/div[1]/div/app-org-info-details/div/div[1]/div[1]/div[2]"
            technologies = wait.until(EC.presence_of_element_located((By.XPATH, tech_xpath))).text.strip()

            org_data[name] = technologies
            count += 1

            # Print progress updates every 10 organizations
            if count % 10 == 0:
                print(f"Scraped: {count} of 185")
            elif count == 185:
                print("Done")

        except Exception as e:
            print(f"Failed to scrape {url}: {e}")

    driver.quit()
    return org_data


def clean_technologies(data):
    """
    Cleans technologies by removing extra spaces and commas.

    Args:
        data (dict): Dictionary with organization names and technologies.

    Returns:
        dict: Cleaned dictionary.
    """
    return {key: ", ".join(value.replace(",", " ").split()) for key, value in data.items()}


def filter_organizations(df, allowed_techs, terms_to_remove):
    """
    Filters organizations based on allowed technologies and removes unwanted ones.

    Args:
        df (pd.DataFrame): DataFrame containing organization details.
        allowed_techs (set): Set of allowed technologies.
        terms_to_remove (set): Set of technologies to remove.

    Returns:
        dict: Filtered dictionary.
    """
    filtered_data = {
        row['Organization']: ", ".join({t.strip().lower() for t in row['Technologies'].split(",")})
        for _, row in df.iterrows()
        if allowed_techs & {t.strip().lower() for t in row['Technologies'].split(",")}
    }

    # Remove organizations containing unwanted technologies
    return {
        k: v for k, v in filtered_data.items()
        if not any(term in v.lower().replace(" ", "") for term in terms_to_remove)
    }


def save_to_csv(data, filename):
    """
    Saves the dictionary to a CSV file.

    Args:
        data (dict): Dictionary with organization names and technologies.
        filename (str): Name of the CSV file.
    """
    df = pd.DataFrame(list(data.items()), columns=['Organization', 'Technologies'])
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")


def main():
    """
    Runs the full scraping pipeline and filters organizations based on user input.
    """
    print("Scraping organization links...")
    href_list = get_org_links()
    print(f"A total of {len(href_list)} organizations were found")

    print("\nScraping organization details...")
    data = scrape_org_details(href_list)

    # Clean technologies
    data = clean_technologies(data)

    # Save raw data
    save_to_csv(data, "gsoc_data.csv")

    # Ask if the user wants to filter
    filter_choice = input("\nDo you want to filter the data? (yes/no): ").strip().lower()
    if filter_choice != "yes":
        print("Exiting without filtering.")
        return

    # Get allowed technologies from user
    allowed_techs = set(input("Enter allowed technologies (comma-separated): ").lower().split(","))
    allowed_techs = {t.strip() for t in allowed_techs}

    # Get technologies to remove from user
    terms_to_remove = set(input("Enter technologies to remove (comma-separated): ").lower().split(","))
    terms_to_remove = {t.strip().replace(" ", "") for t in terms_to_remove}

    # Load the saved DataFrame
    gsoc_df = pd.read_csv("gsoc_data.csv")

    # Apply filtering
    filtered_dict = filter_organizations(gsoc_df, allowed_techs, terms_to_remove)

    # Save filtered data
    save_to_csv(filtered_dict, "mgsoc_data.csv")

    filter_choice = input("\nDo you want to filter even more? (yes/no): ").strip().lower()
    if filter_choice != "yes":
        print("Exiting without filtering.")
        return

    terms_to_remove = set(input("Repeat terms you wanted removed before and add new ones").lower().split(","))
    terms_to_remove = {t.strip().replace(" ", "") for t in terms_to_remove}

    # Load the saved DataFrame
    gsoc_df = pd.read_csv("gsoc_data.csv")

    # Apply filtering
    filtered_dict = filter_organizations(gsoc_df, allowed_techs, terms_to_remove)

    # Save filtered data
    save_to_csv(filtered_dict, "mgsoc_data.csv")


if __name__ == "__main__":
    main()


