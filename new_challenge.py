from twilio.rest import Client
from conf import account_sid, auth_token, db_user, db_pwd
from pymongo import MongoClient
import datetime
from utils import update_flow_state, send_base_message, send_message

db = MongoClient('localhost', 27017,
                 username=db_user, password=db_pwd, authSource='maintenant', authMechanism='SCRAM-SHA-1')

sms_client = Client(account_sid, auth_token)


def send_new_challenges():
    users = db.maintenant.users.find({})
    for user in users:
        if 'Batch' in user and user['Batch'] != 1 and user['Batch'] != 2:
            send_new_challenge(user)


def send_new_challenge(user, bypass_flow_state=False):
    if 'flow_state' in user and user['flow_state'] == 'challenge_sent' and not bypass_flow_state:
        return "0"
    next_challenge_id = find_next_challenge_id(user)
    new_challenge = db.maintenant.challenges.find_one({'challenge_id': next_challenge_id})
    print(new_challenge['initial_message'])
    send_message(user, new_challenge['initial_message'])
    send_base_message(user, 'SMS11')
    update_db_after_new_challenge(user, next_challenge_id)

    return new_challenge['initial_message']


def update_db_after_new_challenge(user, next_challenge_id):
    db.maintenant.users.update_one({'_id': user['_id']}, {'$set': {
        'current_challenge_id': next_challenge_id}})

    update_flow_state(user, 'challenge_sent')
    db.maintenant.results.insert_one({
        'challenge_id': next_challenge_id,
        'state': 'current',
        'relance': 0,
        'date': datetime.datetime.utcnow(),
        'user_id': user['_id']
    })


def find_next_challenge_id(user):

    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"

    last_challenge_id = user_results[0]['challenge_id']
    challenges = db.maintenant.results.find({})
    if last_challenge_id == challenges.count():
        last_challenge_id = 0

    try_next = True
    next_challenge_id = last_challenge_id + 1
    while try_next:
        next_challenges = db.maintenant.results.find({'user_id': user['_id'], 'challenge_id': next_challenge_id}).sort('date', -1)
        if next_challenges.count() == 0:
            return next_challenge_id
        next_challenge = next_challenges[0]

        if next_challenge['relance'] == 1:
            return next_challenge_id
        next_challenge_id = next_challenge_id + 1
        if next_challenge_id > challenges.count() + 1:
            try_next = False

    print("All challenges done for user {}".format(user['_id']))


if __name__ == '__main__':
    send_new_challenges()
