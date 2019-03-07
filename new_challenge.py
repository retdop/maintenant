import datetime
from utils import update_flow_state, send_base_message, send_challenge_message
from database import db
from flow_states import feedback_asked, relance_asked, challenge_sent, number_verified
from time import sleep


def send_new_challenges():
    users = db.maintenant.users.find({})
    for user in users:
        if 'Batch' in user and user['Batch'] != 1 and user['Batch'] != 2:
            send_new_challenge(user)
            sleep(5)


def send_new_challenge(user, bypass_flow_state=False):
    if not bypass_flow_state and 'flow_state' in user and \
            not (user['flow_state'] == feedback_asked
                 or user['flow_state'] == relance_asked
                 or user['flow_state'] == number_verified):
        return "0"
    next_challenge_id = find_next_challenge_id(user)
    if next_challenge_id:
        send_challenge_message(user, next_challenge_id)
        send_base_message(user, 'SMS11')
        update_db_after_new_challenge(user, next_challenge_id)

    return "OK"


def update_db_after_new_challenge(user, next_challenge_id):
    db.maintenant.users.update_one({'_id': user['_id']}, {'$set': {
        'current_challenge_id': next_challenge_id}})

    update_flow_state(user, challenge_sent)
    db.maintenant.results.insert_one({
        'challenge_id': next_challenge_id,
        'state': 'current',
        'relance': 0,
        'date': datetime.datetime.utcnow(),
        'user_id': user['_id']
    })


def find_next_challenge_id(user):
    challenges = db.maintenant.challenges.find({})

    user_results = db.maintenant.results.find({'user_id': user['_id']}).sort('date', -1)
    if user_results.count() == 0:
        return 1

    # check if all challenges has been made or make the lowest one
    user_results_cid = db.maintenant.results.find({'user_id': user['_id']}).sort('challenge_id', 1)
    if user_results_cid.count() == 0:
        return 1

    challenge_id_index = 0
    for result in user_results_cid:
        current_challenge_id = result['challenge_id']
        if current_challenge_id == challenge_id_index:
            pass
        if current_challenge_id == challenge_id_index + 1:
            challenge_id_index += 1
            pass
        if current_challenge_id > challenge_id_index + 1:
            return challenge_id_index + 1

    if challenge_id_index < challenges.count():
        return challenge_id_index + 1

    last_challenge_id = user_results[0]['challenge_id']
    if last_challenge_id == challenges.count():
        last_challenge_id = 0

    try_next = True
    second_loop = False
    next_challenge_id = last_challenge_id + 1
    while try_next:
        next_challenges = db.maintenant.results.find({'user_id': user['_id'], 'challenge_id': next_challenge_id}) \
            .sort('date', -1)
        if next_challenges.count() == 0:
            return next_challenge_id
        next_challenge = next_challenges[0]

        if next_challenge['relance'] == 1:
            return next_challenge_id
        next_challenge_id = next_challenge_id + 1
        if next_challenge_id > challenges.count():
            if not second_loop:
                second_loop = True
                next_challenge_id = 1
            else:
                try_next = False

    update_flow_state(user, 'all_done')
    print("All challenges done for user {}".format(user['_id']))


if __name__ == '__main__':
    send_new_challenges()
