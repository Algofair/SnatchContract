import sys
import base64

from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk import account, mnemonic, wallet, kmd, encoding

def compile_program(client, fname) :
    data = open(fname, 'r').read()
    compile_response = client.compile(data)
    return base64.b64decode(compile_response['result'])

def wait_for_confirmation(client, txid) :
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        #print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    #print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo

def get_private_key_from_mnemonic(mn) :
    private_key = mnemonic.to_private_key(mn)
    return private_key

algod_address = sys.argv[1]
algod_token = sys.argv[2]
kmd_address = sys.argv[3]
kmd_token = sys.argv[4]
wallet_name = sys.argv[5]
wallet_pwd = sys.argv[6]

kmd = kmd.KMDClient(kmd_token, kmd_address)
wallet = wallet.Wallet(wallet_name, wallet_pwd, kmd)
client = algod.AlgodClient(algod_token, algod_address)

# define creator
creator = sys.argv[7]
creator_private_key = wallet.export_key(creator)

# get node suggested parameters
params = client.suggested_params()
# comment out the next two (2) lines to use suggested fees
params.flat_fee = True
params.fee = int(sys.argv[8])

# create unsigned transaction
approval_program = compile_program(client, sys.argv[9])
clear_program = compile_program(client, sys.argv[10])

escrow_contract = compile_program(client, sys.argv[11])
txn = transaction.ApplicationUpdateTxn(creator, params, app_id, approval_program, clear_program, [escrow_contract])

# sign transaction
signed_txn = txn.sign(creator_private_key)
tx_id = signed_txn.transaction.get_txid()

# send transaction
client.send_transactions([signed_txn])

# await confirmation
wait_for_confirmation(client, tx_id)
