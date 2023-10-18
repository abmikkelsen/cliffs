##### 
# Function ## function to download and analyse papers from google scholar
# - This function will do a google scholar search based on a query (food + hazard)
# - It will attempt to download the first 20 results (mostly through scihub)
# - Then ChatPDF will check through each pdf and answer your question and find quotes within each pdf

# You need
# 1. To install PyPaperBot (you can do this in anaconda terminal by typing *pip install PyPaperBot*
# 2. A chatPDF API Key. you can get this by making a chatPDF user and clicking *My Account* on the ChatPDF API website https://www.chatpdf.com/docs/api/backend



# food systems & climate change
# pypaperbot download papers; chatpdf read papers 
# Anna Mikkelsen, Oct 2023


import requests
import glob
import PyPaperBot
from PyPaperBot import __main__ as p
import os
import time
import pandas as pd
import re



# FUNCTIONS to download and review the papers
def download_papers(food, hazard, scholar_pages=[1,2], scholar_results=20, skip_if_folder_exists = True):
    '''
    Searches a query on google scholar and downloads the specified number of papers on the specified google scholar page counts of food and hazard for specific pages & number of articles, which are downloaded to a local folder

    Arguments:
    -----------
        food: str
            food, or species/item being impacted
        hazard: str
            hazard or impact on food
        scholar_pages: list of integers. 
            list of pages to search. default: [1,2]
        scholar_results: int
            number of papers to search and download
        skip_if_folder_exists: bool
            if true, will load papers downloaded in folder {food}_{hazard} if it exists

    Returns:    
    -----------
        pdfs: list of filepaths 
            list containing all pdfs downloaded in the query
    '''


    # specify download folder
    folder_name = f'{food}_{hazard}'
    dwn_dir = os.path.join(os.getcwd(), folder_name)
    if (os.path.exists(dwn_dir)) and (skip_if_folder_exists):
        pdfs = glob.glob(os.path.join(dwn_dir, '*.pdf'))
        print('found %d papers in the folder "%s"' %(len(pdfs), folder_name))
    else: 
        os.mkdir(dwn_dir)
        # make query:
        query = f'{food}+{hazard}'
        #download papers from google scholar
        p.start(query=query, scholar_pages=scholar_pages, scholar_results=scholar_results, dwn_dir=dwn_dir, proxy=[])

        pdfs = glob.glob(os.path.join(dwn_dir, '*.pdf'))
        print('downloaded %d of %d papers' %(len(pdfs), scholar_results))
    return pdfs


def upload_analyze_papers(food, hazard, pdfs, API_Key, question='default'):
    '''
    analyzes content of each pdf file and answers the question asked
        1. each pdf is loaded in chatpdf (at a rate of 12/minute to avoid timeout errors for free api accounts)
        2. then question is answered
        3. and saved into a pandas dataframe 

    Arguments:
    -----------
        food: str
            food, or species/item being impacted
        hazard: str
            hazard or impact on food
        pdfs: list of filepaths 
            list containing all pdfs downloaded in the query
        API_Key: str
            API key for chatpdf. Get api key from https://www.chatpdf.com/docs/api/backend
        question: str
            question to ask about pdf. can be a multipart quesiton
            

    Returns:    
    -----------
        pdfs: list of filepaths 
            list containing all pdfs downloaded in the query
    '''

    all_results = pd.DataFrame(columns=['filename', 'food', 'hazard', 'quote', 'location', 'pos/neg', 'how']) 

    # Load papers into chatpdf
    # dummy loop to only upload 12/minute
    uploads = 0
    start_time = time.time()

    for file in pdfs:
        # Check if we've reached the upload limit
        if uploads >= 12:
            elapsed_time = time.time() - start_time
            if elapsed_time < 60:
                # If uploads exceed the limit in less than a minute, wait for the remaining time
                wait_time = 60 - elapsed_time
                print(f'Upload limit reached. Waiting for {wait_time:.2f} seconds...')
                time.sleep(wait_time)
            uploads = 0  # Reset the counter and start a new minute
            start_time = time.time()

        print(f'loading file "{os.path.basename(file)}" ')
        files = [('file', ('file', open(file, 'rb'), 'application/octet-stream'))]
        headers = {'x-api-key': API_Key}
        response = requests.post('https://api.chatpdf.com/v1/sources/add-file', headers=headers, files=files)
        
        # Update the upload counter
        uploads += 1

        if response.status_code == 200:
            sID = response.json()['sourceId']
        else:
            print('Status:', response.status_code)
            print('Error:', response.text)
            continue

        # 'Read' papers in chatpdf
        headers = {
            'x-api-key': API_Key,
            "Content-Type": "application/json"
        }
        print('analyzing file...')
        if question == 'default':
            question = f'1a) provide a quote from the text about how {hazard} impacts {food}? 2a) in what region is this study 3a) does {hazard} negatively or positively impact {food} (reply only negatvie/positive) 4a) exactly how is {food} impacted?'

        data = {
            'sourceId': sID,
            'messages': [
                {
                    'role': "user",
                    'content': question,
                }
            ]
        }
        response = requests.post(
            'https://api.chatpdf.com/v1/chats/message', headers=headers, json=data)

        if response.status_code == 200:
            print('result:', response.json()['content'])
            results = response.json()['content']
            segments = results.split('a)')  # Split the text using regex
            if len(segments) >= 4:
                quote = segments[0].strip()
                location = segments[1].strip()
                page = segments[2].strip()
                paragraph = segments[3].strip()

                # Create a row dictionary for this PDF
                row_data = {
                    'filename': os.path.basename(file),
                    'food': food,
                    'hazard': hazard,
                    'quote': quote,
                    'location': location,
                    'pos/neg': page,
                    'how': paragraph
                }

                # Append the row data to the results
                all_results = pd.concat([all_results, pd.DataFrame([row_data])], ignore_index=True)
        else:
            print('Status:', response.status_code)
            print('Error:', response.text)
        print("\n")

    return all_results



# combined function to download and review
def download_read_export(food, hazard, API_Key, scholar_pages=[1,2], scholar_results=20, question='default', skip_if_folder_exists = True):

    '''
    Combines the functions above to 
        1. download pdfs from google scholar
        2. analyze each pdf 

    Arguments:
    -----------
        food: str
            food, or species/item being impacted
        hazard: str
            hazard or impact on food
        API_Key: str
            API key for chatpdf. Get api key from https://www.chatpdf.com/docs/api/backend
        question: str
            question to ask about pdf. can be a multipart quesiton
        skip_if_folder_exists: bool
            if true, will load papers downloaded in folder {food}_{hazard} if it exists

    Returns:    
    -----------
        pdfs: list of filepaths 
            list containing all pdfs downloaded in the query
    '''

    start_time = time.time() #start timer

    pdfs = download_papers(food, hazard, scholar_pages, scholar_results, skip_if_folder_exists)
    df = upload_analyze_papers(food, hazard,pdfs, API_Key, question='default')
    return df

    end_time = time.time() #stop timer
    elapsed_time = end_time - start_time
    print(f'Time taken for "{food}" and "{hazard}":{elapsed_time:.2f} seconds')




