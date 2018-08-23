import hashlib
import json
import requests

from textwrap import dedent
from time import time
from urllib.prase import urlparse
from uuid import uuid4

from flask import Flask, jsonify, request

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

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
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates proof. Extracted for use in validating chain.

        Items of interest:
            last_proof - (int)
            proof      - (int)
            return     - (bool)
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "1234"
    
    def register_node(self, address):
        """
        Add to list of nodes.

        Items of interest:
            address - (str) - Address of node.
            return  - (None)
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Determine if given blockchain is valid (using longest chain as authority).

        Items of interest:
            chain  - (list) - Blockchain.
            return - (bool) - Validity of blockchain.
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block['previous_hash'] != self.hash(last_block):
                return False
            
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Consensus algo, resolves conflicts by replacing
        conflicting chain with the longest one in the network.

        Items of interest:
            return - (bool) - If chain was replaced successfully.
        """

        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f"http://{node}/chain")

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        
        return False


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
        'message':       "New block forged.",
        'index':         block['index'],
        'transactions':  block['transactions'],
        'proof':         block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return "Missing values in this new transaction POST.", 400
    
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    
    response = {
        'message': f"Transaction will be added to Block {index}"
    }

    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Please supply valid list of nodes.", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': "New nodes have been added.",
        'total_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': "Our chain was replaced.",
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'message': "Our chain is authoritative.",
            'chain': blockchain.chain,
        }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host = '127.0.0.1', port = 5000)