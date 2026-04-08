import requests
from bs4 import BeautifulSoup


url = 'https://app.diagnocat.eu/patients/'  # Replace with the website you want to crawl
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    print("Successfully fetched the webpage!")
else:
    print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
    

# Parse the content using BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Print the parsed content
print(soup.prettify())  # To view the page structure