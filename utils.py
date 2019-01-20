import requests
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from conf import account_sid, auth_token, from_number, device_id, access_token
from database import db
from bson.objectid import ObjectId


sms_client = Client(account_sid, auth_token)


def send_base_message(user, sms_id):
    good_user = verify_user(user)
    message = db.maintenant.messages.find_one({'sms_id': sms_id})
    return send_message(good_user, message['content'])


def send_challenge_message(user, challenge_id):
    good_user = verify_user(user)
    new_challenge = db.maintenant.challenges.find_one({'challenge_id': challenge_id})
    return send_message(good_user, new_challenge['initial_message'])


def send_message_twilio(user, content):
    msg = sms_client.messages.create(
        body=content,
        from_=from_number,
        to=make_nice_phone_number(user['Tlphone'])
    )
    print('New message sent to {} {} from {} ({})'.format(user['Prnom'], user['Nom'], from_number, msg.sid))
    return msg.sid


def send_message_free(user, content):
    r = requests.post('https://smsgateway.me/api/v4/message/send',
                      headers={
                          'Authorization': access_token
                      },
                      json=[{
                              'phone_number': make_nice_phone_number(user['Tlphone']),
                              'message': content,
                              'device_id': device_id
                          }],
                      verify=False
                      )
    print('New message sent to {} {} (code {})'.format(user['Prnom'], user['Nom'], r.status_code))
    return r.text


send_message = send_message_free
resp_message = send_message


def resp_message_twilio(user, content):
    resp = MessagingResponse()
    resp.message(content)
    print('New message sent to {} {} from {}'.format(user['Prnom'], user['Nom'], from_number))
    return str(resp)


def get_user(phone_number):
    # this is ugly
    user = db.maintenant.users.find_one({'Tlphone': int(phone_number.replace(' ', '')[-9:])})
    if not user:
        # try with spaces and leading zero
        ten_digit = '0' + phone_number.replace(' ', '')[-9:]
        spaces_number = ' '.join(a+b for a,b in zip(ten_digit[::2], ten_digit[1::2]))
        user = db.maintenant.users.find_one({'Tlphone': spaces_number})
        if not user:
            # try with french indic code
            # TODO: add other countries
            user = db.maintenant.users.find_one({'Tlphone': int('33' + phone_number.replace(' ', '')[-9:])})
    return user


def update_flow_state(user, new_flow_state):
    good_user = verify_user(user)
    db.maintenant.users.update_one({'_id': good_user['_id']}, {'$set': {'flow_state': new_flow_state}})


def get_user_from_id(user_id):
    user = db.maintenant.users.find_one({'_id': user_id})
    if not user:
        print('user not found')
    return user


def verify_user(user):
    if type(user) == str:
        return get_user_from_id(ObjectId(user))
    elif type(user) == ObjectId:
        return get_user_from_id(user)
    else:
        return user


def make_nice_phone_number(phone_number):
    return '+33' + str(phone_number).replace(' ', '')[-9:]


if __name__ == '__main__':
    user_ = db.maintenant.users.find_one({'Nom': 'Bastard'})
    send_message(user_, 'Test1')
