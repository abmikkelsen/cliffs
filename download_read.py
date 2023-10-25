##### 
# food systems # climate change
# pypaperbot download papers; chatpdf read papers 
# abm Oct 2023



import requests
import glob
import PyPaperBot
from PyPaperBot import __main__ as p
import os
import time
import pandas as pd
import re

#Function to import food list csv and add to search terms
def import_foodlist(filename):
    df = pd.read_csv(filename)
    
    #extract data from columns
    foodname_data = df['Foodname'].tolist()
    species_data = df['Species'].tolist()
    other_data = df['OtherName'].tolist()

    #remove nan from foodname and other
    foodname_datac = [x for x in foodname_data if str(x) != 'nan']
    other_datac = [x for x in other_data if str(x) != 'nan']

    #remove duplicates from foodname and other
    foodname_datacd = list(set(foodname_datac))
    other_cd = list(set(other_datac))

    #split other list by /
    #### need to check for / with spaces
    other_datacds = [x for x in other_cd for x in x.split('/')]

    #create a dictionary to store the lists
    foodlist = {
        'foodname': foodname_datacd,
        'species': species_data,
        'othername': other_datacds
    }
    
    return foodlist


# FUNCTIONS to download and review the papers

def download_papers(food, hazard, scholar_pages=[1,2], scholar_results=20, skip_if_folder_exists = True):
  ## ----------------------------------- ###
    # specify download folder
    folder_name = f'{food}_{hazard}'
    dwn_dir = os.path.join(os.getcwd(), folder_name)
    if os.path.exists(dwn_dir) and skip_if_folder_exists:
        pdfs = glob.glob(os.path.join(dwn_dir, '*.pdf'))
        print('found %d papers in the folder "%s"' %(len(pdfs), folder_name))
    else: # not os.path.exists(dwn_dir)
        os.mkdir(dwn_dir)
        # make query:
        query = f'{food}+{hazard}'
        #download papers from google scholar
        p.start(query=query, scholar_pages=scholar_pages, scholar_results=scholar_results, dwn_dir=dwn_dir, proxy=[])

        pdfs = glob.glob(os.path.join(dwn_dir, '*.pdf'))
        print('downloaded %d of %d papers' %(len(pdfs), scholar_results))
    return pdfs


def upload_analyze_papers(list,food, hazard, pdfs, API_Key, question='default'):
    
    all_results = pd.DataFrame(columns=['filename', 'foodname','species','othername', 'hazard', 'quote', 'location', 'pos/neg', 'how','howquote']) 


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
            question = f'1a) provide a quote from the text about how {hazard} impacts {food}? 2a) in what region is this study 3a) does {hazard} negatively or positively impact {food} (reply only negatvie/positive) 4a) would you classify the impact on {food} as direct physiology, indirect abiotic, or indirect biotic?  5) can you give a quote providing an example of this?'

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
            if len(segments) >= 5:
                quote = segments[1].strip()
                location = segments[2].strip()
                posneg = segments[3].strip()
                how = segments[4].strip()
                howquote = segments[5].strip()

                # Create a row dictionary for this PDF
                row_data = {
                    'filename': os.path.basename(file),
                    list: food,
                    'hazard': hazard,
                    'quote': quote,
                    'location': location,
                    'pos/neg': posneg,
                    'how': how,
                    'howquote': howquote
                }

                # Append the row data to the results
                all_results = pd.concat([all_results, pd.DataFrame([row_data])], ignore_index=True)
        else:
            print('Status:', response.status_code)
            print('Error:', response.text)
        print("\n")

    return all_results

def download_read_export(list, food, hazard, API_Key, scholar_pages=[1,2], scholar_results=20, question='default', skip_if_folder_exists = True):
    start_time = time.time() #start timer

    pdfs = download_papers(food, hazard, scholar_pages, scholar_results, skip_if_folder_exists)
    df = upload_analyze_papers(list,food, hazard,pdfs, API_Key, question='default')
    return df

    end_time = time.time() #stop timer
    elapsed_time = end_time - start_time
    print(f'Time taken for "{food}" and "{hazard}":{elapsed_time:.2f} seconds')


############# Run it

# foods = ['wheat']#, 'rice', 'tuna', 'apple', 'coffee']
# hazards = ['heatwave']#, ['drought', 'heatwave', 'warming', 'storm', 'flooding']
# API_Key = 'sec_6LIDxgLBHBqmhkVam818PYYXqervcPSX' #make a user and get api key from https://www.chatpdf.com/docs/api/backend
# scholar_pages = [1,2]
# scholar_results = 5
# question  = 'default' #f'1a) provide a quote from the text about how {hazard} impacts {food}? 2a) in what region is this study 3a) does {hazard} negatively or positively impact {food} (reply only negatvie/positive) 4a) exactly how is {food} impacted?'

# # Create an empty dataframe to store the results
# dfall = pd.DataFrame(columns=['filename', 'food', 'hazard', 'quote', 'location', 'pos/neg', 'how']) ## Specify a question in quotes or use the default: "How does {hazard} impact {food}? can you provide a quote from the text about this?"
# skip_if_folder_exists = True ## dummy variable, if you have the data downloaded already and dont want to re-download it. defualt=True

# # Create an empty dataframe to store the results
# #dfall = pd.DataFrame(columns=['food', 'hazard', 'quote', 'location', 'page', 'paragraph'])

# ## Run function across combinations of food and hazard
# for food in foods:
#   for hazard in hazards:
#     df = download_read_export(food, hazard, API_Key, scholar_pages=scholar_pages, scholar_results=scholar_results, question=question, skip_if_folder_exists = True)
#     dfall = pd.concat([dfall, df], ignore_index=True)

# # Print the merged dataframe
# print(dfall)



