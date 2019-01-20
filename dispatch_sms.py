from flask import Flask, request, session
from conf import session_key
from new_challenge import send_new_challenge
from update_collections import new_users
from utils import update_flow_state, get_user, send_base_message, send_challenge_message
from flow_states import feedback_asked, relance_asked, challenge_sent, verif_number, number_verified
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import re
from database import db


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
        return unsubscribe(user)

    return sms_dispatch[user['flow_state']](message, user)


def parse_note(body):
    try:
        note = int(body)
    except ValueError:
        try:
            note = int(re.search('[0-9]', body).group())
        except (AttributeError, ValueError):
            note = 0
    if note > 5:
        note = 5
    if note < 0:
        note = 0
    return note


def parse_relance(body):
    validated_message = ''.join(x for x in body if x.isalpha()).lower()
    relance = 0
    if validated_message == 'oui':
        relance = 1
    if validated_message != 'oui' and validated_message != 'non':
        relance = 1
    return relance


def parse_challenge_response(challenge_response):
    validated_message = ''.join(x for x in challenge_response if x.isalpha() or x == '!' or x == '?').lower()
    if validated_message != '!' and validated_message != '?' and validated_message.lower() != 'suivant':
        validated_message = '!'
    return validated_message


def receive_note_and_ask_relance(message, user):
    # flow_state : feedback_asked
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_results_id = user_results[0]['_id']

    note = parse_note(message)

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'note': note}})

    update_flow_state(user, relance_asked)

    if note < 3:
        return send_base_message(user, 'SMS32')
    else:
        return send_base_message(user, 'SMS31')


def receive_relance_and_send_challenge(message, user):
    # flow_state : relance_asked
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"
    last_challenge_results_id = user_results[0]['_id']

    relance = parse_relance(message)

    db.maintenant.results.update_one({
        '_id': last_challenge_results_id},
        {'$set': {'relance': relance}})

    return send_new_challenge(user)


def receive_response_and_continue(message, user):
    # flow_state : challenge_sent
    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return "1"

    last_challenge_id = user_results[0]['challenge_id']
    challenge_response = parse_challenge_response(message)
    if challenge_response == '?':
        send_challenge_message(user, last_challenge_id, option='?')
    elif challenge_response.lower() == 'suivant':
        return send_new_challenge(user, bypass_flow_state=True)
    else:
        send_challenge_message(user, last_challenge_id, option='!')
    return "OK"


def receive_verif_number_and_welcome(message, user):
    # flow_state : verif_number
    verif_number_response = message.lower().replace(' ', '')

    if verif_number_response == 'oui':
        update_flow_state(user, number_verified)
    else:
        return unsubscribe(user)

    return send_base_message(user, 'SMS2')


def unsubscribe(user):
    # This will never happen because twilio catches the STOP message before us!
    print('user {} {} wants to unsubscribe'.format(user['Prnom'], user['Nom']))
    return "OK"


def do_nothing(message, user):
    print('user {} {} is on number_verfied but sent a message'.format(user['Prnom'], user['Nom']))
    print(message)
    return 'OK'


sms_dispatch = {
    feedback_asked: receive_note_and_ask_relance,
    relance_asked: receive_relance_and_send_challenge,
    challenge_sent: receive_response_and_continue,
    verif_number: receive_verif_number_and_welcome,
    number_verified: do_nothing
}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
