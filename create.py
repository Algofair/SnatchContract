import sys
import base64
from subprocess import check_output
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

# define escrow as creator first
escrow = sys.argv[7]
game = sys.argv[13]
app_args = sys.argv[8].split(",")

li = [encoding.decode_address(game), encoding.decode_address(escrow)]
for i in app_args:
	li.append(int(i).to_bytes(8, 'big'))

app_args = li

# declare application state storage (immutable)
local_ints = 2
local_bytes = 0
global_ints = 15
global_bytes = 4

# define schema
global_schema = transaction.StateSchema(global_ints, global_bytes)
local_schema = transaction.StateSchema(local_ints, local_bytes)

# declare on_complete as NoOp
on_complete = transaction.OnComplete.NoOpOC.real

# get node suggested parameters
params = client.suggested_params()
# comment out the next two (2) lines to use suggested fees
params.flat_fee = True
params.fee = int(sys.argv[12])

# create unsigned transaction
approval_program = compile_program(client, sys.argv[9])
clear_program = compile_program(client, sys.argv[10])
txn = transaction.ApplicationCreateTxn(creator, params, on_complete, approval_program,  clear_program, global_schema, local_schema, app_args)

# sign transaction
signed_txn = txn.sign(creator_private_key)
tx_id = signed_txn.transaction.get_txid()

# send transaction
client.send_transactions([signed_txn])

# await confirmation
wait_for_confirmation(client, tx_id)

# display results
transaction_response = client.pending_transaction_info(tx_id)
app_id = transaction_response['application-index']

# Compile stateless escrow, old escrow deprecated
out = check_output(['python3', sys.argv[11], str(app_id)])
response = client.compile(out.decode("utf-8"))
txn = transaction.ApplicationUpdateTxn(creator, params, app_id, approval_program, clear_program, [encoding.decode_address(response['hash'])])

# sign transaction
signed_txn = txn.sign(creator_private_key)
tx_id = signed_txn.transaction.get_txid()

# send transaction
client.send_transactions([signed_txn])

# await confirmation
wait_for_confirmation(client, tx_id)

print('{ "app_id" : "' + str(app_id)  + '", "escrow_addr" : "' + response['hash'] + '", "program": "' + response['result'] + '" }')