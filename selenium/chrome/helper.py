from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import time
import sys
import os
import json

# Set the path to the ChromeDriver executable
CHROME_DRIVER_PATH = "/home/dkaneria/workspace/cmu/research/video-cca-identifier/setup_cloudlab/chromedriver-linux64/chromedriver"

# file_name = sys.argv[1]
file_name = "netflix"

# Set up Chrome options
options = Options()
# options.add_argument('--headless')

# Set up logs directory
logs_dir = os.path.dirname(os.path.dirname(os.getcwd())) + "/logs/"
os.makedirs(logs_dir, exist_ok=True)  # Create logs directory if it doesn't exist

options.add_argument("--log-net-log=" + logs_dir + file_name + ".json")
# options.add_argument('--ignore-certificate-errors')
options.add_argument("--auto-open-devtools-for-tabs")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_argument("--disable-extensions-except=../har-export-trigger-0.6.0")
options.add_argument("--load-extension=../har-export-trigger-master-0.6.0")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-popup-blocking")
options.add_argument("--disable-notifications")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
# options.add_argument("--enable-quic")

# Initialize the Chrome driver using Service
service = Service(executable_path=CHROME_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

time.sleep(2)

# Wait up to 10 minutes for operations to complete
wait = WebDriverWait(driver, 600)  # 600 seconds = 10 minutes

# JavaScript to trigger HAR export
har_harvest = """
myString = HAR.triggerExport().then(harLog => {
    return JSON.stringify(harLog);
});
return myString
"""

def save_har_file(file_name):
    """Save HAR data to a file"""
    with open(logs_dir + file_name + ".har", "w+") as f:
        f.write('{ "log" : ')
        f.write(driver.execute_script(har_harvest))
        f.write("}")

def convert_to_one_har(file_name, count):
    """Combine multiple HAR files into one"""
    if count == 0:
        save_har_file(file_name)
    else:
        new_har_data = []
        for num in range(1, count + 1):
            with open(logs_dir + file_name + str(num) + ".har", "r") as har_file:
                temp_har_data = json.load(har_file)
                new_har_data += temp_har_data['log']['entries']
        
        with open(logs_dir + file_name + "1" + ".har", "r") as base_har_file:
            har_data = json.load(base_har_file)
        
        har_data['log']['entries'] = new_har_data
        
        with open(logs_dir + file_name + ".har", "w+") as f:
            json.dump(har_data, f)

def quit_driver():
    """Close the browser and quit the driver"""
    time.sleep(2)
    print("Quitting")
    driver.quit()

# Example usage:
# Navigate to a website, perform actions, then:
# save_har_file(file_name)
# convert_to_one_har(file_name, count)
# quit_driver()