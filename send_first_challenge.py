from twilio.rest import Client
from conf import account_sid, auth_token, db_user, db_pwd
from pymongo import MongoClient
from utils import send_base_message, send_message
from new_challenge import update_db_after_new_challenge, find_next_challenge_id

db = MongoClient('localhost', 27017,
                 username=db_user, password=db_pwd, authSource='maintenant', authMechanism='SCRAM-SHA-1')

sms_client = Client(account_sid, auth_token)


def send_new_challenges():
    users = db.maintenant.users.find({})
    for user in users:
        if 'Batch' in user and user['Batch'] != 1 and user['Batch'] != 2:
            send_new_challenge(user)


def send_new_challenge(user, bypass_flow_state=False):
    # send only to people with number_verified
    if 'flow_state' in user and user['flow_state'] != 'number_verified' and not bypass_flow_state:
        return "0"
    next_challenge_id = find_next_challenge_id(user)
    new_challenge = db.maintenant.challenges.find_one({'challenge_id': next_challenge_id})
    print(new_challenge['initial_message'])
    send_message(user, new_challenge['initial_message'])
    send_base_message(user, 'SMS11')
    update_db_after_new_challenge(user, next_challenge_id)
    return new_challenge['initial_message']


if __name__ == '__main__':
    send_new_challenges()
