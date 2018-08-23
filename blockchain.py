import hashlib
import json

from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Adds new block to chain.

        Items of interest:
            proof         - (int)  - Proof for Proof of Work algo.
            previous_hash - (Optional, str)
            return        - (dict) - The new block.
        """
        
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Wipe list of transactions.
        self.current_transactions = []

        self.chain.append(block)

        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Adds new transaction to transaction list.

        Items of interest:
            sender    - (str) - Address of the Sender
            recipient - (str) - Address of the Recipient
            amount    - (int) 
            return    - (int) - Index of the Block that holds the transaction.
        """
        
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        SHA-256 hash of given block.

        Items of interest:
            block  - (dict) - Block to be hashed.
            return - (str)  - The hash itself.
        """
        # Orders dictionary to prevent inconsistent hashes.
        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """
        Returns last block...

        Items of interest:
            return - (dict) - The block.
        """
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Proof of work for this blockchain.

        Algo:
            - Find number x such that when hashed with previous proof,
              the hash leads with "1234".

        Items of interest:
            last_proof - (int)
            return     - (int)
        """

        proof = 0
        valid_proof = False

        while valid_proof is False:
            guess = f'{last_proof}{proof}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            valid_proof = guess_hash[:4] == "1234"

            # Prevents increase in proof value on final loop.
            if valid_proof is False:
                proof += 1

        return proof



# Instantiate Node, generate unique identifier, instantiate the Blockchain.
app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    blockchain.new_transaction(
        sender = "0",
        recipient = node_identifier,
        amount = 1,
    )

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New block forged.",
        'index': block['index'],
        'transaction': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return "Missing values", 400
    
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    
    response = {
        'message': f'Transaction will be added to Block {index}'
    }

    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000)