import csv
import os
import warnings

import numpy as np
import pandas as pd
import yfinance as yf
from dateutil.relativedelta import relativedelta

import lstm_calculator
import news_contents_sentimental_analysis

warnings.filterwarnings('ignore', category=FutureWarning)
import tensorflow as tf

WEIGHT_FOR_LSTM_VALUE = 0.6  # 가중치 a: LSTM 가중치
WEIGHT_FOR_EMOTIONAL_ANALYSIS_VALUE = 0.3  # 가중치 b: 감성분석 점수 가중치
WEIGHT_FOR_PER_VALUE = 0.1  # 가중치 c: PER 점수 가중치

PATH = "./"
os.chdir(PATH)
DIR = 'prediction_score'
STOCK_DIR = 'stock'


def mkdir(company_code):
    if not os.path.exists(f"./{DIR}/{company_code}"):
        os.makedirs(f"./{DIR}/{company_code}")


def start(company_code, learning_date):
    mkdir(company_code)

    learning_start_date = learning_date - relativedelta(days=30)
    for i in range(30):
        with open(f"./{lstm_calculator.DIR}/{company_code}/{company_code}_{learning_start_date}.csv", 'r', -1,
                  'utf-8') as lines:
            next(lines)

            for line in csv.reader(lines):
                lstm_prediction = round(float(line[0]))
                previous_closing_price = round(float(line[1]))

        lstm_value = (lstm_prediction - previous_closing_price) / previous_closing_price  # (다음날 예측 종가 - 오늘 종가) / 오늘 종가
        # 감성분석 값 불러오기
        emotional_analysis_csv = news_contents_sentimental_analysis.calculate_two_weeks(company_code,
                                                                                        learning_start_date)

        # PER 값 불러오기
        company_per_csv = 0
        same_category_per_csv = 0
        try:
            with open('./per_data/csv/' + company_code + '.csv', 'r', -1, 'utf-8') as lines:
                next(lines)

                for line in csv.reader(lines):
                    company_per_csv = float(line[2])
                    same_category_per_csv = float(line[3])
        except FileNotFoundError:
            company_per_csv = 0
            same_category_per_csv = 0

        # 자기 회사 PER 이랑 동일업종 PER 이 모두 양수인 경우에만 per_value 계산
        if company_per_csv > 0 and same_category_per_csv > 0:
            per_value_csv = 1 - company_per_csv / same_category_per_csv  # 1 - 자기 회사 PER / 동일 업종 PER
        else:
            per_value_csv = 0

        result = {
            'LearningDate': [learning_start_date],
            'LstmScore': [float(lstm_value)],
            'EmotionalScore': [emotional_analysis_csv],
            'PerScore': [per_value_csv],
            'PreviousClosingPrice': [previous_closing_price],
        }
        prediction_df = pd.DataFrame(result, columns=["LearningDate", "LstmScore", "EmotionalScore", "PerScore",
                                                      "PreviousClosingPrice"])
        if i == 0:
            prediction_df.to_csv(f"./{DIR}/{company_code}/{company_code}.csv", index=False, header=True)
        else:
            prediction_df.to_csv(f"./{DIR}/{company_code}/{company_code}.csv", index=False, mode='a', header=False)

        learning_start_date = learning_start_date + relativedelta(days=1)

    stock_start_date = learning_date - relativedelta(days=30)
    stock_info = yf.download(company_code + '.KS', start=learning_date - relativedelta(days=40), end=learning_date)

    # stock = pd.read_csv(f"./{STOCK_DIR}/{company_code}.KS.csv")

    # stock_info = stock_info.set_index(['Date'])
    # while stock_start_date:

    start_date = stock_start_date
    while stock_info.loc[
          start_date.strftime("%Y-%m-%d"):(start_date + relativedelta(days=1)).strftime("%Y-%m-%d")].empty:
        start_date -= relativedelta(days=1)

    start_closing_price = \
        stock_info.loc[start_date.strftime("%Y-%m-%d"):(start_date + relativedelta(days=1)).strftime("%Y-%m-%d")][
            "Close"][
            0]

    stock_info = stock_info.loc[stock_start_date.strftime("%Y-%m-%d"):learning_date.strftime("%Y-%m-%d")]
    stock_info_date_list = list(stock_info.index)

    stock_info = stock_info.values[0:, 1:].astype(np.float)

    # 날짜 뽑기 x
    # 종가 뽑기 y (x == y)
    # [{x1: y1}, {x2: y2}, {x3: y3}]

    # str(list(stock_info.index)[0].date())

    prices = stock_info[:, -3]  # 한달 치 실제 종가
    zip_iterator = zip(stock_info_date_list, prices)
    temp_date = None
    temp_price = 0
    result = []
    for data in zip_iterator:
        if temp_date is None:
            temp_date = data[0]
            temp_price = data[1]
        else:
            date_gap = (data[0] - temp_date)  # 1, 2, 3
            for _ in range(date_gap.days):
                result.append(temp_price)

            temp_date = data[0]
            temp_price = data[1]

    if stock_info_date_list[-1] != learning_date:
        for _ in range((learning_date - stock_info_date_list[-1].date()).days):
            result.append(temp_price)

    if len(result) != 30:
        for _ in range(30 - len(result)):
            result.insert(0, start_closing_price)
    # result = [82000, 81900, 82300, 82300, 82300]

    xy = pd.read_csv(f"./{DIR}/{company_code}/{company_code}.csv")
    lstm_x = xy.iloc[:, 1]
    emotional_x = xy.iloc[:, 2]
    per_x = xy.iloc[:, 3]
    previous_x = xy.iloc[:, 4]
    today_y = result

    x1 = tf.placeholder(tf.float32, shape=[None])  # lstm score
    x2 = tf.placeholder(tf.float32, shape=[None])  # sentimental score
    x3 = tf.placeholder(tf.float32, shape=[None])  # per score
    x4 = tf.placeholder(tf.float32, shape=[None])  # previous day close
    y = tf.placeholder(tf.float32, shape=[None])  # today close

    w1 = tf.Variable(0.65, dtype=tf.float32, name='w1', constraint=lambda x: tf.clip_by_value(x, 0, 1))
    w2 = tf.Variable(0.25, dtype=tf.float32, name='w2', constraint=lambda x: tf.clip_by_value(x, 0, 1))
    w3 = 1 - (w1 + w2)
    weight_sum = w1 + w2 + w3

    init_op = tf.initialize_all_variables()
    hypothesis = ((x1 * w1 + x2 * w2 + (x3 * w3)) / 10 + 1) * x4
    cost = tf.reduce_mean(tf.square(hypothesis - y))
    optimizer = tf.train.GradientDescentOptimizer(learning_rate=1e-9)
    train = optimizer.minimize(cost)

    final_w1 = 0.0
    final_w2 = 0.0
    final_w3 = 0.0
    with tf.Session() as sess:
        sess.run(init_op)
        for step in range(5):
            cost_val, hy_val, _ = sess.run(
                [cost, hypothesis, train],
                feed_dict={x1: lstm_x, x2: emotional_x, x3: per_x, x4: previous_x, y: today_y}
            )
            if step == 4:
                print(f"\nW1: {sess.run(w1)} W2: {sess.run(w2)} W3: {sess.run(w3)} Sum: {sess.run(weight_sum)}")

                final_w1 = sess.run(w1)
                final_w2 = sess.run(w2)
                final_w3 = sess.run(w3)
            # else:
            #    print(step, "Cost", cost_val, "\nPrediction:\n", hy_val, "\nW3:", sess.run(w3), "\nW2:", sess.run(w2),
            #          "\nW1:", sess.run(w1),
            #          "\nSum", sess.run(weight_sum))

    return final_w1, final_w2, final_w3
    """
    if 부분이 학습을 모두 끝내고 출력하는 거에여 사실 가중치들만 출력하면 되는데 일단 혹시 몰라서 학습내용도 다 출력 시켰습니다.
    final_W1, final_W2, final_W3를 return 하면 최종 가중치들 입니다. 일단 주석 처리 해놓을꼐여 
    이거 return해서 각각 순서대로 lstm, 감성분석, per에 넣어서 계산하면 됩니다.
    """
