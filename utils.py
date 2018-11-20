from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from conf import account_sid, auth_token, from_number
from pymongo import MongoClient
db = MongoClient('localhost', 27017)

sms_client = Client(account_sid, auth_token)


def send_base_message(user, sms_id):
    message = db.maintenant.messages.find_one({'sms_id': sms_id})
    return send_message(user, message['content'])


def send_message(user, content):
    msg = sms_client.messages.create(
        body=content,
        from_=from_number,
        to=make_nice_phone_number(user['Tlphone'])
    )
    print('New message sent to {} {} from {} ({})'.format(user['Prnom'], user['Nom'], from_number, msg.sid))


def resp_message(user, content):
    resp = MessagingResponse()
    resp.message(content)
    print('{} message sent to {} {} from {}'.format('Some', user['Prnom'], user['Nom'], from_number))
    return str(resp)


def get_user(phone_number):
    user = db.maintenant.users.find_one({'Tlphone': int(phone_number.replace(' ', '')[-9:])})
    if not user:
        # try with french indic code
        # TODO: add other countries
        user = db.maintenant.users.find_one({'Tlphone': int('33' + phone_number.replace(' ', '')[-9:])})
    return user


def update_flow_state(user, new_flow_state):
    db.maintenant.users.update_one({'_id': user['_id']}, {'$set': {'flow_state': new_flow_state}})


def make_nice_phone_number(phone_number):
    return '+33' + str(phone_number).replace(' ', '')[-9:]
