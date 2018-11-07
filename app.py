from flask import Flask, redirect, url_for, render_template, request, flash

import os
from os.path import join, dirname
from dotenv import load_dotenv
import braintree
from gateway import generate_client_token, transact, find_transaction
import json
from flask_pymongo import PyMongo
import pay123
import pyqrcode
import png

app = Flask(__name__)
app.config["MONGO_URI"] = '#ENTERMONGOUSER'
mongo = PyMongo(app)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
app.secret_key = os.environ.get('APP_SECRET_KEY')

PORT = int(os.environ.get('PORT', 4567))

TRANSACTION_SUCCESS_STATUSES = [
    braintree.Transaction.Status.Authorized,
    braintree.Transaction.Status.Authorizing,
    braintree.Transaction.Status.Settled,
    braintree.Transaction.Status.SettlementConfirmed,
    braintree.Transaction.Status.SettlementPending,
    braintree.Transaction.Status.Settling,
    braintree.Transaction.Status.SubmittedForSettlement
]

parsedItems = [1]

@app.route('/', methods=['GET'])
def index():
    return render_template('checkouts/cart.html')

@app.route('/checkouts/new', methods=['POST'])
def new_checkout():
    client_token = generate_client_token()
    amount = request.form['amount']
    jsonItems = request.form['items']
    global parsedItems
    parsedItems = json.loads(jsonItems)
    return render_template('checkouts/new.html', client_token=client_token, amount=amount, parsedItems=parsedItems, jsonItems=jsonItems)

@app.route('/checkouts/<transaction_id>', methods=['GET'])
def show_checkout(transaction_id):
    global parsedItems
    transaction = find_transaction(transaction_id)
    result = {}
    if transaction.status in TRANSACTION_SUCCESS_STATUSES:
        result = {
            'header': 'Sweet Success!',
            'icon': 'success',
            'message': 'Your test transaction has been successfully processed. See the Braintree API response and try again.'
        }
        #make a new transaction table entry, {"transaction_id" : value, "jsonItems" : value}
    else:
        result = {
            'header': 'Transaction Failed',
            'icon': 'fail',
            'message': 'Your test transaction has a status of ' + transaction.status + '. See the Braintree API response and try again.'
        }
    return render_template('checkouts/show.html', transaction=transaction, result=result, parsedItems=parsedItems)

@app.route('/checkouts', methods=['POST'])
def create_checkout():
    global parsedItems
    result = transact({
        'amount': request.form['amount'],
        'payment_method_nonce': request.form['payment_method_nonce'],
        'options': {
            "submit_for_settlement": True
        }
    })
    for pair in parsedItems:
        query = mongo.db.paypay.find_one({"name" : pair[0].strip()})
        qty = query["quantity"]
        if int(qty) < pair[1]:
            return pair[0] + " is out of stock."
    if result.is_success or result.transaction:
        jsonItems = request.form['items']
        parsedItems = json.loads(jsonItems) #[[item1, qty], [item2, qty], [item3, qty]]
        #db operations: decrement stock, add new transaction entry
        for pair in parsedItems:
            query = mongo.db.paypay.find_one({"name" : pair[0].strip()})
            qty = query["quantity"]
            newqty = int(qty) - pair[1]
            newvalues = { "$set": {"quantity" : str(newqty)}}
            mongo.db.paypay.update_one(query, newvalues)
        page = "http://0.0.0.0:4567/checkouts/" + str(result.transaction.id)
        url = pyqrcode.create(page)
        url.png('tr.png', scale=8)

        pay123.main()
        return redirect(url_for('show_checkout',transaction_id=result.transaction.id))
    else:
        for x in result.errors.deep_errors: flash('Error: %s: %s' % (x.code, x.message))
        return redirect(url_for('new_checkout'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
