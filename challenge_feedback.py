from twilio.rest import Client
from conf import account_sid, auth_token, db_user, db_pwd
from pymongo import MongoClient
from utils import update_flow_state, send_message


db = MongoClient('localhost', 27017,
                 username=db_user, password=db_pwd, authSource='maintenant', authMechanism='SCRAM-SHA-256')

sms_client = Client(account_sid, auth_token)


def send_feedback_messages():
    users = db.maintenant.users.find({})
    feedback_message = db.maintenant.messages.find_one({'sms_id': 'SMS20'})
    print(feedback_message['content'])
    for user in users:
        send_message(user, feedback_message['content'])
        update_collections_after_end_of_challenge(user)


def update_collections_after_end_of_challenge(user):
    update_flow_state(user, 'feedback_asked')

    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return 1
    last_challenge_results_id = user_results[0]['_id']

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'state': 'done'}})


if __name__ == '__main__':
    send_feedback_messages()
