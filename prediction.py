import csv
import os
from dateutil.relativedelta import relativedelta
import lstm_calculator
import news_contents_sentimental_analysis
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
import tensorflow as tf
import datetime


WEIGHT_FOR_LSTM_VALUE = 0.6  # 가중치 a: LSTM 가중치
WEIGHT_FOR_EMOTIONAL_ANALYSIS_VALUE = 0.3  # 가중치 b: 감성분석 점수 가중치
WEIGHT_FOR_PER_VALUE = 0.1  # 가중치 c: PER 점수 가중치

PATH = "./"
os.chdir(PATH)
DIR = 'prediction_score'
STOCKDIR = 'stock'

def mkdir(company_code):
    if not os.path.exists(f"./{DIR}/{company_code}"):
        os.makedirs(f"./{DIR}/{company_code}")

def start(company_code, learning_date):
    learningstart_date=learning_date-relativedelta(days=30)
    for i in range(30):
        with open(f"./{lstm_calculator.DIR}/{company_code}/{company_code}_{learningstart_date}.csv", 'r', -1,
                  'utf-8') as lines:
            next(lines)

            for line in csv.reader(lines):
                lstm_prediction = round(float(line[0]))
                previous_closing_price = round(float(line[1]))

        lstm_value = (lstm_prediction - previous_closing_price) / previous_closing_price  # (다음날 예측 종가 - 오늘 종가) / 오늘 종가
        # 감성분석 값 불러오기
        emotional_analysis_csv = news_contents_sentimental_analysis.calculate_two_weeks(company_code, learning_date)

        # PER 값 불러오기
        company_per_csv = 0
        same_category_per_csv = 0
        with open('./per_data/' + company_code + '.csv', 'r', -1, 'utf-8') as lines:
            next(lines)

            for line in csv.reader(lines):
                company_per_csv = float(line[3])
                same_category_per_csv = float(line[4])

        # 자기 회사 PER 이랑 동일업종 PER 이 모두 양수인 경우에만 per_value 계산
        if company_per_csv > 0 and same_category_per_csv > 0:
            per_value_csv = 1 - company_per_csv / same_category_per_csv  # 1 - 자기 회사 PER / 동일 업종 PER
        else:
            per_value_csv = 0
    

        result = {
            'LearningDate': [learningstart_date],
            'LstmScore': [float(lstm_value)],
            'EmotionalScore': [emotional_analysis_csv],
            'PerScore': [per_value_csv],
            'PreviousClosingPrice': [previous_closing_price],
        }
        prediction_df = pd.DataFrame(result, columns=["LearningDate", "LstmScore", "EmotionalScore", "PerScore",
                                                      "PreviousClosingPrice"])
        if i==0:
            prediction_df.to_csv(f"./{DIR}/{company_code}/{company_code}.csv", index=False, header=True)
        else:
            prediction_df.to_csv(f"./{DIR}/{company_code}/{company_code}.csv", index=False, mode='a', header=False)

        learningstart_date = learningstart_date + relativedelta(days=1)


    stockstart_date=learning_date-relativedelta(days=29)
    stock = pd.read_csv(f"./{STOCKDIR}/{company_code}.KS.csv")
    #print(stock)
    stock_info = pd.DataFrame(stock)
    stock_info = stock_info.set_index(['Date'])
    stock_info = stock_info.loc[stockstart_date.strftime("%Y-%m-%d"):learning_date.strftime("%Y-%m-%d")]
    stock_info = stock_info.values[0:, 1:].astype(np.float)
    #price = stock_info.iloc[]
    #print(stock_info)
    price = stock_info[:, -3]
    #print(price)
    #print(price.shape)
    xy = pd.read_csv(f"./{DIR}/{company_code}/{company_code}.csv")
    lstm_x = xy.iloc[:, 1]
    emotional_x = xy.iloc[:, 2]
    per_x = xy.iloc[:, 3]
    previous_x = xy.iloc[:, 4]
    #price=price.reshape(15)
    #print(price.shape)
    today_y = price


    X1 = tf.placeholder(tf.float32, shape=[None])
    X2 = tf.placeholder(tf.float32, shape=[None])
    X3 = tf.placeholder(tf.float32, shape=[None])
    X4 = tf.placeholder(tf.float32, shape=[None])
    Y = tf.placeholder(tf.float32, shape=[None])

    W1 = tf.Variable(0.6, dtype=tf.float32, name='W1')
    W2 = tf.Variable(0.3, dtype=tf.float32, name='W2')
    W3 = 1-(W1+W2)

    init_op = tf.initialize_all_variables()
    hypothesis = ((X1*W1 + X2*W2 + X3*W3)/100 + 1) * X4

    cost=tf.reduce_mean(tf.square(hypothesis-Y))
    optimizer = tf.train.GradientDescentOptimizer(learning_rate=1e-6)
    train = optimizer.minimize(cost)
    sess = tf.Session()
    sess.run(init_op)

    for step in range(5):
        cost_val, hy_val, W1_val, W2_val, W3_val, sum, _ = sess.run(
            [cost, hypothesis, W1, W2, W3, W1 + W2 + W3, train],
            feed_dict={X1: lstm_x, X2: emotional_x, X3: per_x, X4: previous_x, Y: today_y}
        )
        if step == 4:
            print(step,"\nFinal Prediction:\n", hy_val[-1], "\nW3:", W3_val, "\nW2:", W2_val, "\nW1:", W1_val, "\nSum", sum)
        else:
            print(step, "Cost", cost_val, "\nPrediction:\n", hy_val, "\nW3:", W3_val, "\nW2:", W2_val, "\nW1:", W1_val,
                  "\nSum", sum)


    """
    predicted_value = 100 * (lstm_value * WEIGHT_FOR_LSTM_VALUE +
                             float(emotional_analysis_value) * WEIGHT_FOR_EMOTIONAL_ANALYSIS_VALUE +
                             per_value * WEIGHT_FOR_PER_VALUE)

    print(f"company_code: {company_code}")
    print(f"learning_date: {learning_date}")
    print(f"predicted_value: {predicted_value}%")
    """






