import csv
import datetime
import os

import pandas as pd

table = dict()

with open('polarity.csv', 'r', -1, 'utf-8') as polarity:
    next(polarity)

    for line in csv.reader(polarity):
        key = str()
        for polarity_word in line[0].split(';'):
            key += polarity_word.split('/')[0]

        table[key] = {'Neg': line[3], 'Neut': line[4], 'Pos': line[6]}

def get_news_list_by_company_code(company_code, date):
    news_list = []
    with open("./date_news_words/" + company_code + "/" + company_code + "_" + str(date)[:10] + '.csv', 'r', -1,
              'utf-8') as news_data:
        next(news_data)

        for news in csv.reader(news_data):
            content = news[2]
            title = news[1]
            news_list.append(content + " " + title)

    return news_list


def analyze(company_code):
    file_stop_word = open('불용어.txt', 'r', -1, 'utf-8')
    stop_words = file_stop_word.read()
    stop_words = set(stop_words.split('\n'))
    file_stop_word.close()

    start_date = datetime.date.today()
    target_date = datetime.date(2021, 5, 12)

    while True:
        negative_list = []
        neutral_list = []
        positive_list = []

        score_word_list = []

        neg_sum = 0
        neu_sum = 0
        pos_sum = 0
        if (start_date - target_date).days < 0:
            break
        news_list = get_news_list_by_company_code(company_code, start_date)

        for news in news_list:
            word_list = news.split()
            negative = 0
            neutral = 0
            positive = 0
            score_word = ""
            for word in word_list:
                if word in stop_words:
                    continue

                if word in table:
                    score_word += word + " "
                    negative += float(table[word]['Neg'])
                    neutral += float(table[word]['Neut'])
                    positive += float(table[word]['Pos'])

            negative_list.append(negative)
            neutral_list.append(neutral)
            positive_list.append(positive)

            score_word_list.append(score_word)

        score_columns = ['negative', 'neutral', 'positive']
        score_df = pd.DataFrame(columns=score_columns)

        rate_columns = ['ratio', 'portion']
        rate_df = pd.DataFrame(columns=rate_columns)

        score_word_columns = ['words']
        score_word_df = pd.DataFrame(columns=score_word_columns)

        ratio_list = []
        portion_list = []
        ratio = 0

        for neg in negative_list:
            neg_sum += neg
        for neu in neutral_list:
            neu_sum += neu
        for pos in positive_list:
            pos_sum += pos

        negative_list.append(neg_sum)
        neutral_list.append(neu_sum)
        positive_list.append(pos_sum)

        if pos_sum != 0:
            ratio = pos_sum / (neg_sum + pos_sum)
            ratio_list.append(ratio)
        else:
            ratio_list.append(0)

        if ratio != 0:
            print(f"rt: {ratio / 0.53 - 1}")
            portion_list.append(ratio / 0.53 - 1)
        else:
            portion_list.append(0)

        rate_df["ratio"] = ratio_list
        rate_df["portion"] = portion_list

        score_df['negative'] = negative_list
        score_df['neutral'] = neutral_list
        score_df['positive'] = positive_list

        score_word_df['words'] = score_word_list

        if not os.path.exists("./date_news_score/" + company_code):
            os.makedirs("./date_news_score/" + company_code)

        if not os.path.exists("./date_news_rate/" + company_code):
            os.makedirs("./date_news_rate/" + company_code)

        if not os.path.exists("./date_news_score_words/" + company_code):
            os.makedirs("./date_news_score_words/" + company_code)

        score_df.to_csv("./date_news_score/" + company_code + "/" + company_code + "_" + str(start_date)[:10] + '.csv',
                        index=False)
        pd.read_csv("./date_news_score/" + company_code + "/" + company_code + "_" + str(start_date)[:10] + '.csv')

        rate_df.to_csv("./date_news_rate/" + company_code + "/" + company_code + "_" + str(start_date)[:10] + '.csv',
                       index=False)
        pd.read_csv("./date_news_rate/" + company_code + "/" + company_code + "_" + str(start_date)[:10] + '.csv')

        score_word_df.to_csv(
            "./date_news_score_words/" + company_code + "/" + company_code + "_" + str(start_date)[:10] + '.csv',
            index=False)
        pd.read_csv(
            "./date_news_score_words/" + company_code + "/" + company_code + "_" + str(start_date)[:10] + '.csv')

        start_date = start_date - datetime.timedelta(days=1)