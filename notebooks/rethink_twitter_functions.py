# function to initialize Twitter API v1.1 instance (for 30-day and full archive search)
def init_api_1():
    
    # importing necessary modules and loading .env file
    from dotenv import load_dotenv
    import os
    import tweepy
    load_dotenv()
    
    # retrieving environment variables from .env file
    consumer_key = os.getenv("API_KEY")
    consumer_secret = os.getenv("API_KEY_SECRET")
    bearer_token = os.getenv("BEARER_TOKEN")
    access_token = os.getenv("ACCESS_TOKEN")
    access_secret = os.getenv("ACCESS_SECRET")
    
    # Twitter API authentication
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    
    # instantiating Twitter API v1.1 reference
    api_1 = tweepy.API(auth, wait_on_rate_limit=True)
    
    return api_1

# function to initialize Twitter API v2 instance (for 7-day search)
def init_api_2():
    # importing necessary modules and loading .env file
    from dotenv import load_dotenv
    import os
    import tweepy
    load_dotenv()
    
    # retrieving environment variables from .env file
    consumer_key = os.getenv("API_KEY")
    consumer_secret = os.getenv("API_KEY_SECRET")
    bearer_token = os.getenv("BEARER_TOKEN")
    access_token = os.getenv("ACCESS_TOKEN")
    access_secret = os.getenv("ACCESS_SECRET")
    
    # instantiating Twitter API v2 reference
    api_2 = tweepy.Client(bearer_token=bearer_token,
                         consumer_key=consumer_key,
                         consumer_secret=consumer_secret,
                         access_token=access_token,
                         access_token_secret=access_secret,
                         wait_on_rate_limit=True)
    
    return api_2

# function to parse Twitter API v2 response into a DataFrame of Tweet data
def tweet_df(df, response, tweet_fields):
    
    users = response.includes['users']
    user_data = {user['id']: [user['public_metrics']['followers_count'], user['verified']] for user in users}
        
    # looping through each Tweet in response, parsing data
    for i in range(len(response.data)):
        tweet = response.data[i]
        tweet_id = tweet.id
        tweet_data = {}
        for field in tweet_fields:
            if tweet[field]:
                tweet_data[field] = tweet[field]
                
                # extracting hashtags from "entities" field and adding it as its own column
                if field == "entities":
                    try:
                        hashtag_data = tweet[field]['hashtags']
                        hashtags = [hashtag['tag'] for hashtag in hashtag_data]
                        tweet_data['entities_hashtags'] = hashtags
                    except KeyError:
                        tweet_data['entities_hashtags'] = None
                
                # separating metrics from "public_metrics" field and adding them as their own column
                if field == "public_metrics":
                    metrics = list(tweet[field].keys())
                    for metric in metrics:
                        tweet_data[metric] = tweet[field][metric]
                
            else:
                tweet_data[field] = None
                if field == "entities":
                    tweet_data['entities_hashtags'] = None
        
        # adding user data to DataFrame
        user = user_data[tweet['author_id']]
        tweet_data['followers_count'] = user[0]
        tweet_data['verified'] = user[1]
        
        df.loc[tweet_id] = tweet_data
    
    return df

# function to retrieve Tweets from the past 7 days relevant to a query
def search_7(query, start_date=None, end_date=None, max_results=20, write_csv=False, filename="search_7.csv"):
    
    # if max_results is large, warn user of large number of API calls
    if max_results > 50000:
        check = input(f'''Warning: Retrieving {max_results} Tweets will result in a large number of API calls. The Twitter API only allows a limited number of calls, so make sure you have the capacity to retrieve {max_results} Tweets.\n\nDo you want to continue? [y/n]\n''')
        while True:
            if check == 'n':
                raise Exception('User stopped function.')
            elif check == 'y':
                break
            else:
                check = input('Please enter either "y" or "n".')
    
    # initializing API v1.1 instance
    api_2 = init_api_2()
    
    # parsing dates passed into function
    from dateutil import parser
    from datetime import datetime
    if start_date:
        start_date = parser.parse(start_date)
        start_date = start_date.strftime("%Y%m%d%H%M")
    if end_date:
        end_date = parser.parse(end_date)
        end_date = end_date.strftime("%Y%m%d%H%M")
    
    # setting Tweet and user data to be included in response
    tweet_fields = ["text", "attachments", "author_id", "context_annotations", "conversation_id", "created_at",
                   "entities", "geo", "in_reply_to_user_id", "lang", "public_metrics", "referenced_tweets"]
    user_fields = ["public_metrics", "verified"]
    
    # initializing variables for API calls and DataFrame for Tweet data
    import pandas as pd
    next_token = None
    num_tweets = 0
    tweets = pd.DataFrame(columns=tweet_fields+['followers_count', 'verified']+
                          ['entities_hashtags','retweet_count','reply_count','like_count','quote_count'])
    tweets.index.name = "Tweet ID"
    
    # making my own pagination loop to further examine the rate limit
    num_loops = 0
    while num_tweets < max_results:
        
        # the API only retrieves between 10 and 100 Tweets per call
        # NOTE: number of API results isn't consistent. max_results=100 doesn't guarantee 100 Tweets in response
        if max_results - num_tweets >= 100:
            num_results = 100
        else:
            num_results = max_results - num_tweets if max_results - num_tweets > 10 else 10
        
        # calling API and searching Tweets over past 7 days
        response = api_2.search_recent_tweets(f"{query} lang:en", 
                                              start_time=start_date,
                                              end_time=end_date,
                                              max_results=num_results,
                                              next_token=next_token,
                                              tweet_fields=tweet_fields,
                                              expansions='author_id',
                                              user_fields=user_fields)
        
        # setting variables for the next loop
        try:
            next_token = response[3]['next_token']
        except KeyError:
            next_token = None
        num_tweets += len(response.data)
        num_loops += 1
        
        # adding Tweet data to DataFrame
        tweets = tweet_df(tweets, response, tweet_fields)
        
    # dropping "public_metrics" since all the values are unpacked, adding "total_engagements"
    tweets.drop('public_metrics', axis=1, inplace=True)
    total_engagements = tweets["retweet_count"] + tweets["reply_count"] + tweets["like_count"] + tweets["quote_count"]
    tweets["total_engagements"] = total_engagements
        
    # writing Tweet DataFrame to csv file
    if write_csv:
        tweets.to_csv(filename)
    
    return tweets

# function to search Tweets within the past 30 days
# utilizes both API v1.1 and v2 to be consistent with 7-day search.
def search_30(query, start_date=None, end_date=None, max_results=20, write_csv=False, filename="search_30.csv"):
    
    # if max_results is large, warn user of large number of API calls
    if max_results > 1000:
        check = input(f'''Warning: Retrieving {max_results} Tweets will result in a large number of API calls. The Twitter API only allows a limited number of calls, so make sure you have the capacity to retrieve {max_results} Tweets.\n\nDo you want to continue? [y/n]\n''')
        while True:
            if check == 'n':
                raise Exception('User stopped function.')
            elif check == 'y':
                break
            else:
                check = input('Please enter either "y" or "n".')
    
    # initializing API v1.1 instance
    api_1 = init_api_1()
    
    # parsing dates passed into function
    from dateutil import parser
    from datetime import datetime
    if start_date:
        start_date = parser.parse(start_date)
        start_date = start_date.strftime("%Y%m%d%H%M")
    if end_date:
        end_date = parser.parse(end_date)
        end_date = end_date.strftime("%Y%m%d%H%M")
    
    # retrieving Tweets from the past 30 days relevant to query using tweepy's pagination function
    import tweepy
    import math
    response_1 = tweepy.Cursor(api_1.search_30_day,
                               label="30day",
                               query=f"{query} lang:en",
                               fromDate=start_date,
                               toDate=end_date,
                               maxResults=100
                              ).pages(math.ceil(max_results/100))
    
    # gathering Tweet ID's in a list
    tweet_ids = []
    for page in response_1:
        tweet_ids.extend([tweet._json['id'] for tweet in page])
    
    # setting Tweet data to be included in response_2
    tweet_fields = ["text", "attachments", "author_id", "context_annotations", "conversation_id", "created_at",
                   "entities", "geo", "in_reply_to_user_id", "lang", "public_metrics", "referenced_tweets"]
    user_fields = ["public_metrics", "verified"]
    
    # initializing variables for API v2 calls and DataFrame for Tweet data
    import pandas as pd
    num_tweets = 0
    tweets = pd.DataFrame(columns=tweet_fields+['followers_count', 'verified']+
                          ['entities_hashtags','retweet_count','reply_count','like_count','quote_count'])    
    tweets.index.name = "Tweet ID"
    
    # loop to retrieve Tweets from ID's through API v2, 100 at a time
    api_2 = init_api_2()
    
    while num_tweets < max_results:
        # slicing tweet_ids since API v2 get_tweets only takes max 100 ID's per request
        try:
            slice_ids = tweet_ids[num_tweets:num_tweets+100]
        except IndexError:
            slice_ids = tweet_ids[num_tweets:]
        if len(slice_ids) == 0:
            break

        # retrieving Tweet data from API v2 and adding to DataFrame
        response_2 = api_2.get_tweets(slice_ids, tweet_fields=tweet_fields, 
                                      expansions='author_id', user_fields=user_fields)
        tweets = tweet_df(tweets, response_2, tweet_fields)
        num_tweets += len(response_2.data)
    
    # dropping "public_metrics" since all the values are unpacked, adding "total_engagements"
    tweets.drop('public_metrics', axis=1, inplace=True)
    total_engagements = tweets["retweet_count"] + tweets["reply_count"] + tweets["like_count"] + tweets["quote_count"]
    tweets["total_engagements"] = total_engagements
    
    # writing Tweet DataFrame to csv file
    if write_csv:
        tweets.to_csv(filename)
    
    return tweets

# function to search Tweets within the full Tweet archive
# utilizes both API v1.1 and v2 to be consistent with 7-day search.
def search_full(query, start_date=None, end_date=None, max_results=20, write_csv=False, filename="search_full.csv"):
    
    # if max_results is large, warn user of large number of API calls
    if max_results > 1000:
        check = input(f'''Warning: Retrieving {max_results} Tweets will result in a large number of API calls. The Twitter API only allows a limited number of calls, so make sure you have the capacity to retrieve {max_results} Tweets.\n\nDo you want to continue? [y/n]\n''')
        while True:
            if check == 'n':
                raise Exception('User stopped function.')
            elif check == 'y':
                break
            else:
                check = input('Please enter either "y" or "n".')
            
    # initializing API v1.1 instance
    api_1 = init_api_1()
    
    # parsing dates passed into function
    from dateutil import parser
    from datetime import datetime
    if start_date:
        start_date = parser.parse(start_date)
        start_date = start_date.strftime("%Y%m%d%H%M")
    if end_date:
        end_date = parser.parse(end_date)
        end_date = end_date.strftime("%Y%m%d%H%M")
    
    # retrieving Tweets from the full tweet archive relevant to query using tweepy's pagination function
    import tweepy
    import math
    response_1 = tweepy.Cursor(api_1.search_full_archive,
                               label="full",
                               query=f"{query} lang:en",
                               fromDate=start_date,
                               toDate=end_date,
                               maxResults=100
                              ).pages(math.ceil(max_results/100))
    
    # gathering Tweet ID's in a list
    tweet_ids = []
    for page in response_1:
        tweet_ids.extend([tweet._json['id'] for tweet in page])
    
    # setting Tweet data to be included in response
    tweet_fields = ["text", "attachments", "author_id", "context_annotations", "conversation_id", "created_at",
                   "entities", "geo", "in_reply_to_user_id", "lang", "public_metrics", "referenced_tweets"]
    user_fields = ["public_metrics", "verified"]
    
    # initializing variables for API calls and DataFrame for Tweet data
    import pandas as pd
    tweets = pd.DataFrame(columns=tweet_fields+["followers_count", "verified"]+
                          ['entities_hashtags','retweet_count','reply_count','like_count','quote_count'])
    tweets.index.name = "Tweet ID"
    
    # loop to retrieve Tweets from ID's through API v2, 100 at a time
    api_2 = init_api_2()
    num_tweets = 0
    while num_tweets < max_results:
        # slicing tweet_ids since API v2 get_tweets only takes max 100 ID's per request
        try:
            slice_ids = tweet_ids[num_tweets:num_tweets+100]
        except IndexError:
            slice_ids = tweet_ids[num_tweets:]
        if len(slice_ids) == 0:
            break

        # retrieving Tweet data from API v2 and adding to DataFrame
        response_2 = api_2.get_tweets(slice_ids, tweet_fields=tweet_fields,
                                     expansions='author_id', user_fields=user_fields)
        tweets = tweet_df(tweets, response_2, tweet_fields)
        num_tweets += len(response_2.data)
    
    # dropping "public_metrics" since all the values are unpacked, adding "total_engagements"
    tweets.drop('public_metrics', axis=1, inplace=True)
    total_engagements = tweets["retweet_count"] + tweets["reply_count"] + tweets["like_count"] + tweets["quote_count"]
    tweets["total_engagements"] = total_engagements
    
    # writing Tweets DataFrame to csv file
    if write_csv:
        tweets.to_csv(filename)
    
    return tweets

def word_cloud(df, query=None, save_imgs=False):
    # combining DataFrame text column into one long string, doing some initial pre-processing
    import pandas as pd
    tweet_text = " ".join(df["text"])
    tweet_text = tweet_text.lower()
    tweet_text = tweet_text.replace("\n", " ")
    
    # splitting string into set of words, removing hashtags, usernames, links, and retweet indicator
    word_list = set(tweet_text.split(" "))
    hash_list = {word for word in word_list if word.startswith("#")}
    user_list = {word for word in word_list if word.startswith("@")}
    link_list = {word for word in word_list if word.startswith("http")}
    word_list = {word for word in word_list if word not in hash_list.union(user_list, link_list)}
    word_list = {word for word in word_list if word != "rt"}
    
    # using nltk tokenizer to further pre-process text, removing non-alpha words
    from nltk.tokenize import word_tokenize
    import nltk
    nltk.download('punkt')
    tweet_text = " ".join(word_list)
    word_list = word_tokenize(tweet_text)
    word_list = {word for word in word_list if word.isalpha()}
    
    # joining list of words into final cleaned string
    tweet_text = " ".join(word_list)
    
    # generating word cloud
    from wordcloud import WordCloud, STOPWORDS
    import matplotlib.pyplot as plt
    import re

    stopwords = set(STOPWORDS)
    
    # adding words from query to stop words so they don't show up in the word cloud
    if query:
        pattern = re.compile('[\W_]+')
        query_split = query.lower().split()
        query_stops = {pattern.sub('', word) for word in query_split}
        stopwords.update(query_stops)

    # word cloud for text
    words_fig = plt.figure()
    word_cloud = WordCloud(background_color="white", width=3000, height=2000, max_font_size=500,
                           max_words=100, prefer_horizontal=1.0, stopwords=stopwords)
    word_cloud.generate(tweet_text)
    plt.imshow(word_cloud)
    plt.axis("off")
    plt.title("Frequent keywords in Tweets", fontsize=15)
    plt.show()
    if save_imgs:
        word_cloud.to_file("wordcloud.png")

    # word cloud for hashtags
    hash_fig = plt.figure()
    word_cloud = WordCloud(background_color="white", width=3000, height=2000, max_font_size=500,
                           max_words=100, prefer_horizontal=1.0, stopwords=stopwords)
    word_cloud.generate(" ".join(hash_list))
    plt.imshow(word_cloud)
    plt.axis("off")
    plt.title("Frequent hashtags in Tweets", fontsize=15)
    plt.show()
    if save_imgs:
        word_cloud.to_file("hashtags.png")
    
    return words_fig, hash_fig

# plot function
def attention_plots(dfs, query_labels=None, title="Tweet count over time",
                    xlabel="month", plot_type="line", figsize=(10,5)):
    
    # ensuring the correct parameters have been passed
    assert plot_type in ("line", "bar"), "Please input 'line' or 'bar' into plot_type"
    assert xlabel in ("day", "month", "year"), "Please input 'day', 'month', or 'year' into xlabel"
    
    import pandas as pd
    if type(dfs) == pd.core.frame.DataFrame:
        dfs = [dfs]
    elif type(dfs) in (list, set, tuple):
        if query_labels:
            assert len(dfs) == len(query_labels), "Please make sure that the query_labels argument is the same length as the number of DataFrames."
    
    # creating figure for plot
    import matplotlib.pyplot as plt
    figure = plt.figure(figsize=figsize)
    
    # looping through dfs and creating plots for each
    for i in range(len(dfs)):
        df = dfs[i]
        label = query_labels[i]
        
        # converting dates to datetime, getting counts of tweets per day
        df["created_at"] = pd.to_datetime(df["created_at"])
        daily_counts = df.groupby(df["created_at"].dt.date).count()
        dates = pd.to_datetime(daily_counts.index)

        # line or bar graph, depending on input
        if plot_type == "line":
            plt.plot(daily_counts.index, daily_counts["text"], label=label)
        else:
            plt.bar(daily_counts.index, daily_counts["text"], label=label)
    
    # setting x-axis ticks to be month, day, or year, depending on input
    if xlabel == "month":
        period = "M"
        tick_labels = dates.to_period(period).unique().strftime("%b %Y")
    elif xlabel == "day":
        period = "D"
        tick_labels = dates.to_period(period).unique().strftime("%m-%d-%Y")
    elif xlabel == "year":
        period = "Y"
        tick_labels = dates.to_period(period).unique()
    tick_locs = dates.to_period(period).unique()
    plt.xticks(ticks=tick_locs, labels=tick_labels, rotation=60)
    
    # setting plot title and subtitle (if query is passed)
    plt.suptitle(title, fontsize=15)
    plt.xlabel("Date")
    plt.ylabel("Number of Tweets")
    plt.legend(loc=0)
    plt.show()
    
    return figure
