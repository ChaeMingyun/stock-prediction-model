import per_crawler
import news_contents_crawler as crawler
import news_contents_sentiment as sentiment
import preprocess_kosac as preprocess

# 삼전, SK하이닉스, NAVER, 카카오
company_code_list = ['005930', '000660', '035420', '035720']

if __name__ == '__main__':
    # start PER crawling
    per_crawler.start()

    # start NEWS crawling
    crawler.start(company_code_list)
    for company_code in company_code_list:
        preprocess.start(company_code)
        sentiment.text_processing(company_code)
