from flask import Flask, request, session
from conf import session_key, db_user, db_pwd
from pymongo import MongoClient
from new_challenge import send_new_challenge
from update_collections import new_users
from utils import update_flow_state, get_user, send_base_message, resp_message
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

db = MongoClient('localhost', 27017,
                 username=db_user, password=db_pwd, authSource='maintenant', authMechanism='SCRAM-SHA-1')

sentry_sdk.init(
    dsn="https://361d7688867b44db99cd55f9b15333e3@sentry.io/1327058",
    integrations=[FlaskIntegration()]
)


SECRET_KEY = session_key
app = Flask(__name__)
app.config.from_object(__name__)


@app.route("/users", methods=['GET', 'POST'])
def receive_new_users():
    """Triggers a users collection update"""
    print('new users?')
    new_users()
    return 'done'


@app.route("/sms", methods=['GET', 'POST'])
def reception():
    """Gets the messages history."""
    # Increment the counter
    counter = session.get('counter', 0)
    counter += 1

    # Save the new counter value in the session
    session['counter'] = counter
    user_number = request.json['phone_number']
    message = request.json['message']
    user = get_user(user_number)
    if not user:
        return 'NOK'
    if message.lower() == 'stop':
        unsubscribe(user)

    return sms_dispatch[user['flow_state']](message, user)


def parse_note(body):
    try:
        note = int(body)
    except ValueError:
        note = 0
    if note > 5:
        note = 5
    if note < 0:
        note = 0
    return note


def parse_relance(body):
    relance = 0
    if body == 'oui':
        relance = 1
    if body != 'oui' and body != 'non':
        relance = 1
    return relance


def parse_challenge_response(challenge_response):
    if challenge_response != '!' and challenge_response != '?' and challenge_response.lower() != 'suivant':
        challenge_response = '!'
    return challenge_response


def receive_note_and_ask_relance(message, user):
    # flow_state : feedback_asked
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_results_id = user_results[0]['_id']

    note = parse_note(message.replace(' ', ''))

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'note': note}})

    update_flow_state(user, 'relance_asked')

    if note < 3:
        return send_base_message(user, 'SMS32')
    else:
        return send_base_message(user, 'SMS31')


def receive_relance_and_ask_remarks(message, user):
    # flow_state : relance_asked
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_results_id = user_results[0]['_id']

    relance = parse_relance(message.lower().replace(' ', ''))

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'relance': relance}})

    update_flow_state(user, 'remarks_asked')

    return send_base_message(user, 'SMS40')


def receive_remarks_and_send_challenge(message, user):
    # flow_state : remarks_asked
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_results_id = user_results[0]['_id']

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'remarks': message}})

    return send_new_challenge(user)


def receive_response_and_continue(message, user):
    # flow_state : challenge_sent
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_id = user_results[0]['challenge_id']

    challenge_response = parse_challenge_response(message.replace(' ', ''))
    challenge = db.maintenant.challenges.find_one({'challenge_id': last_challenge_id})
    if challenge_response == '!':
        message = challenge['exclam_message']
    elif challenge_response == '?':
        message = challenge['why_message']
    elif challenge_response.lower() == 'suivant':
        return send_new_challenge(user, bypass_flow_state=True)
    else:
        message = challenge['exclam_response']

    return resp_message(user, message)


def receive_verif_number_and_welcome(message, user):
    # flow_state : verif_number
    verif_number_response = message.lower().replace(' ', '')

    if verif_number_response == 'oui':
        update_flow_state(user, 'number_verified')
    else:
        print('user {} {} wants to unsubscribe'.format(user['Prnom'], user['Nom']))

    message = db.maintenant.messages.find_one({'sms_id': 'SMS2'})

    return resp_message(user, message['content'])


def unsubscribe(user):
    # This will never happen because twilio catches the STOP message before us!
    print('user {} {} wants to unsubscribe'.format(user['Prnom'], user['Nom']))


sms_dispatch = {
    'feedback_asked': receive_note_and_ask_relance,
    'relance_asked': receive_relance_and_ask_remarks,
    'remarks_asked': receive_remarks_and_send_challenge,
    'challenge_sent': receive_response_and_continue,
    'verif_number': receive_verif_number_and_welcome
}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
