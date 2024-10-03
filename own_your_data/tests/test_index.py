# TODO
# import os
# from pathlib import Path
#
# import pytest
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
#
# test_file_path = Path(Path(__file__).parent).parent.parent
#
#
# @pytest.fixture(scope="module")
# def browser():
#     service = Service(ChromeDriverManager().install())
#     options = webdriver.ChromeOptions()
#     options.add_argument("--headless")
#     driver = webdriver.Chrome(service=service, options=options)
#     yield driver
#     driver.quit()
#
#
# def test_index_html(browser):
#     browser.get(f"file:///{test_file_path}/index.html")
#     assert browser.title == 'Own Your Data'
