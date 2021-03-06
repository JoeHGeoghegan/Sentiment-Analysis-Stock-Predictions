import os
import requests
import pandas as pd
import datetime as dt
import alpaca_trade_api as tradeapi
import json
from alpaca_trade_api.rest import REST, TimeFrame
from newsapi import NewsApiClient
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("NEWSAPI_KEY")

newsapi = NewsApiClient(api_key=api_key)


# get ohlcv data for individual stock with alpaca api call and make into a dataframe

alpaca_key = os.getenv("ALPACA_API_KEY")
alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")

tradeapi = REST(alpaca_key, alpaca_secret_key)

def get_daily_trade_data(ticker, start_date_str, end_date_str, tradeapi): 
    ticker_df = tradeapi.get_bars(
        ticker,
        TimeFrame.Day,
        start_date_str,
        end_date_str
    ).df
    ticker_df['symbol'] = ticker

    return ticker_df



# create a dataframe of closing prices and ticker symbols from a list of ticker symbols

ticker_list = pd.read_csv('./Data/Cleaned_Data/Ticker_library.csv')['Ticker'].to_list()

def make_tickers_df(ticker_list, start_date_str, end_date_str, tradeapi):
    ticker_dfs_list = [get_daily_trade_data(ticker, start_date_str, end_date_str, tradeapi) for ticker in ticker_list]
    tickers_df = pd.concat(ticker_dfs_list, axis=0, join='outer')
    tickers_df.index = tickers_df.index.date
    tickers_df = tickers_df[['symbol','close','volume']]
    return tickers_df



# use list of tickers to make dictionary with tickers as keys and ohlcv data as values (could be useful for alternative data manipulation)

def make_tickers_dict(ticker_list, start_date_str, end_date_str, tradeapi):
    return {ticker: get_daily_trade_data(ticker, start_date_str, end_date_str, tradeapi) for ticker in ticker_list}


# making a dataframe using news api

company_df = pd.read_csv('./Data/Cleaned_Data/Ticker_library.csv')
company_df = company_df.rename(columns={'Company Name': 'Company_Name'})
company_dict = dict(zip(company_df.Company_Name, company_df.Ticker))
company_list = list(company_dict.keys())

api_key = os.getenv("NEWSAPI_KEY")

newsapi = NewsApiClient(api_key=api_key)


# bin stock returns

def return_bin(df):
    
    bins = [-1000, -0.08, -0.03, -0.0000001, 0.0000001, 0.03, 0.08, 1000]
    labels = ['large loss','medium loss','small loss','no gain/loss','small gain','medium gain','large gain']
    
    df['returns'] = df['close'].pct_change()
    df['return_bin'] = pd.cut(df['returns'], bins=bins, labels=labels)
    df['return_bin'] = df['return_bin'].fillna('no gain/loss')
    return df

#Get news articles on certain topic based on keywords
def get_news(keywords):  
    news_article = newsapi.get_everything(
            q = keywords, 
            language='en', 
            sort_by= 'relevancy',
    )
    return news_article

#Creates dataframe of the articles chosen 
def form_df(keywords):
    news = get_news(keywords)['articles']

    articles = []
    for article in news:

        try:
            date = article['publishedAt'][:10]
            text = article['content']
            ticker = company_dict[keywords]
            articles.append({
                'date' : date,
                'ticker': ticker,
                'text' : text,
            })
        except AttributeError:
            pass
    
    return pd.DataFrame(articles)


# Vader Analyzer

from newsapi import NewsApiClient
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

nltk.download('vader_lexicon')

analyzer = SentimentIntensityAnalyzer()

def vader_analyzer(df):
    analyzer = SentimentIntensityAnalyzer()
    df['compound'] = [analyzer.polarity_scores(x)['compound'] for x in df['text']]
    df['neg'] = [analyzer.polarity_scores(x)['neg'] for x in df['text']]
    df['neu'] = [analyzer.polarity_scores(x)['neu'] for x in df['text']]
    df['pos'] = [analyzer.polarity_scores(x)['pos'] for x in df['text']]

    df['date'] = pd.to_datetime(
    df['date'],
    infer_datetime_format = True,
    utc = True    
    )
    df['date'] = df['date'].dt.date
    
    return df


# perform vader sentiment analysis on dataframe with text and groupby date 
# to get average daily sentiment and unique dates for each row

def daily_sentiment(df):
    vader_df = vader_analyzer(df)
    vader_df = vader_df.groupby(['ticker','date'])['ticker','pos','neg','neu','compound'].mean().reset_index()
    vader_df = vader_df[['date','ticker','pos','neg','neu','compound']]
    return vader_df


# filters through all csv files in Cleaned_Data and returns dataframe of all data for selected stock ticker

def stock_picker(ticker):
    
    stock_df_list = []
    file_path = '../Notebooks/Data/Cleaned_Data'

    for filename in os.listdir(file_path):
        if filename.endswith(".csv") and filename != 'Ticker_library.csv':
            csv_df = pd.read_csv(file_path +'/'+ filename, parse_dates=True, infer_datetime_format=True,index_col='date')
            csv_df = csv_df.loc[csv_df['ticker'] == ticker]
            csv_df.drop(columns='ticker',axis=1,inplace=True)
            stock_df_list.append(csv_df)
    all_ticker_data_df = pd.concat(stock_df_list,axis=1,join='outer')
    all_ticker_data_df.insert(0, 'ticker', ticker)
    return all_ticker_data_df.drop(columns='Unnamed: 0')


keywords = {
    'NFLX': ['NFLX', 'nflx', 'Netflix', 'netflix'],
    'FB': ['FB', 'fb', 'Facebook', 'facebook'],
    'UBER': ['UBER', 'uber', 'Uber'],
    'MCHP': ['MCHP', 'mchp', 'Microchip Technology'],
    'ABNB': ['ABNB', 'abnb', 'AirBnB', 'airbnb'],
    'FANG': ['FANG', 'fang', 'Diamondback Energy', 'diamondback energy', 'Diamondback', 'diamondback'],
    'MRO': ['MRO', 'mro', 'Marathon Oil', 'marathon oil'],
    'DVN': ['DVN', 'dvn', 'Devon Energy', 'devon energy'],
    'SPWR': ['SPWR', 'spwr', 'SunPower', 'Sunpower', 'sunpower'],
    'REGI': ['REGI', 'regi', 'Renewable Energy Group', 'renewable energy group'],
    'MTRX': ['MTRX', 'mtrx', 'McKinsey & Company', 'McKinsey & Co', 'Mckinsey & Co', 'McKinsey', 'Mckinsey', 'mckinsey'],
    'BLK': ['BLK', 'blk', 'BlackRock', 'Blackrock', 'blackrock'],
    'PYPL': ['PYPL', 'pypl', 'PayPal', 'Paypal', 'paypal'],
    'MELI': ['MELI', 'meli', 'MercadoLibre', 'Mercadolibre', 'mercadolibre'],
    'SOFI': ['SOFI', 'sofi', 'SoFi', 'Sofi']
}