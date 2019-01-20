from utils import send_base_message, send_challenge_message
from new_challenge import update_db_after_new_challenge, find_next_challenge_id
from database import db
from flow_states import number_verified
from time import sleep


def send_new_challenges():
    users = db.maintenant.users.find({})
    for user in users:
        if 'Batch' in user and user['Batch'] != 1 and user['Batch'] != 2:
            send_new_challenge(user)
            sleep(5)


def send_new_challenge(user, bypass_flow_state=False):
    # send only to people with number_verified
    if 'flow_state' in user and user['flow_state'] != number_verified and not bypass_flow_state:
        return "0"
    next_challenge_id = find_next_challenge_id(user)
    send_challenge_message(user, next_challenge_id)
    send_base_message(user, 'SMS11')
    update_db_after_new_challenge(user, next_challenge_id)
    return "OK"


if __name__ == '__main__':
    send_new_challenges()
