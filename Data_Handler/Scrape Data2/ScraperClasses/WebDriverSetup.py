
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class WebDriverSetup:
    def __init__(self):
        self.service = Service(ChromeDriverManager().install())
        self.options = webdriver.ChromeOptions()
        #self.options.add_argument("--headless")  # Uncomment to run in the background
        self.driver = webdriver.Chrome(service=self.service, options=self.options)

    def get_driver(self):
        return self.driver

    def close(self):
        self.driver.quit()