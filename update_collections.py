import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pymongo import MongoClient
from twilio.rest import Client
from conf import account_sid, auth_token, db_user, db_pwd
from utils import update_flow_state, send_message

db = MongoClient('localhost', 27017,
                 username=db_user, password=db_pwd, authSource='maintenant', authMechanism='SCRAM-SHA-256')

sms_client = Client(account_sid, auth_token)


def get_spreadsheet_data(spreadsheet):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('Maintenant-co-18e27771f6d8.json', scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(spreadsheet).sheet1

    data = wks.get_all_records()
    return data


def update_collection(spreadsheet, collection):
    data = get_spreadsheet_data(spreadsheet)
    db.maintenant[collection].delete_many({})
    inserted_ids = db.maintenant[collection].insert_many(data).inserted_ids

    print('Succesfully inserted {} documents in {} from {}'.format(len(inserted_ids), collection, spreadsheet))


def update_all_collections():
    update_collection('Défis', 'challenges')
    update_collection('inscrits_from_squarespace', 'users')
    update_collection('Messages de base', 'messages')


def new_users():
    collection = 'users'
    spreadsheet = 'inscrits_from_squarespace'
    users = list(db.maintenant.users.find({}))
    users_tel = [user['Tlphone'] for user in users]

    spreadsheet_users = get_spreadsheet_data('inscrits_from_squarespace')
    spreadsheet_users_tel = [user['Tlphone'] for user in spreadsheet_users]

    new_users_tel = list(set(spreadsheet_users_tel).difference(users_tel))

    db.maintenant[collection].delete_many({})
    inserted_ids = db.maintenant[collection].insert_many(spreadsheet_users).inserted_ids

    print('Succesfully inserted {} documents in {} from {}'.format(len(inserted_ids), collection, spreadsheet))

    for tel in new_users_tel:
        welcoming_committee(tel)


def welcoming_committee(tel):
    user = db.maintenant.users.find_one({'Tlphone': tel})
    if 'flow_state' in user:
        return 0
    welcome_message = db.maintenant.messages.find_one({'sms_id': 'SMS1'})
    send_message(user, welcome_message['content'])

    update_flow_state(user, 'verif_number')


if __name__ == '__main__':
    # new_users()
    update_all_collections()
