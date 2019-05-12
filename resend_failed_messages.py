import requests
from conf import access_token
from utils import send_message, get_user
from time import sleep


def resend_failed_messages(limit):
    r = requests.post('https://smsgateway.me/api/v4/message/search',
                      headers={
                          'Authorization': access_token
                      },
                      json={
                          'filters': [
                              [{
                                  'field': 'status',
                                  'operator': '=',
                                  'value': 'failed'
                              }]
                          ],
                          'order_by': [
                              {
                                  'field': 'created_at',
                                  'direction': 'desc'
                              }
                          ],
                          'limit': limit,
                          'offset': 0
                      },
                      verify=False
                      )
    results = r.json()['results']
    for m in reversed(results):
        print(m['phone_number'], m['created_at'])
        user = get_user(m['phone_number'])
        print(user['Prnom'], m['message'])
        send_message(user, m['message'])
        sleep(5)


if __name__ == '__main__':
    resend_failed_messages(249)
