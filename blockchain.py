import hashlib
import json

import requests
from textwrap import dedent
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from flask import Flask, jsonify, request



class Blockchain(object):
    ##############
    # definition #
    ##############
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # genesis block
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Creates new block in chain
        
        :param proof: <int> proof given by POW algorithm
        :param previous_hash: (Optional) <str> hash of previous block
        :return: <dict> new block
        """
        block = {
                    'index': len(self.chain) + 1,
                    'timestamp': time(),
                    'transactions': self.current_transactions,
                    'proof': proof,
                    'previous_hash': previous_hash or self.hash(self.chain[-1]),
                }
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined block
        :param sender: <str> address of sender
        :param recipient: <str> address of recipient
        :return: <int> index of block
        """
        self.current_transactions.append({
                'sender': sender,
                'recipient': recipient,
                'amount': amount
            })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Create  SHA-256 hash of a block

        :param block: <dict> Block
        :return: <str>
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    #########
    # nodes #
    #########     
    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: <str> Address of node.
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    ##########
    # proofs #
    ##########
    def proof_of_work(self, last_proof):
        """
        Simple POW algorithm
        - Find a number p' such that hash(p*p') contains four 
        leading zeros where p is the proof for the previous block

        :param last_proof:  <int> (p) above
        :return: <int> (p') above
        """
        proof = 0
        while not self.is_valid_proof(last_proof, proof):
            proof += 1
        return proof

    @staticmethod
    def is_valid_proof(last_proof, proof):
        """
        Validates *proof* iff hash(last_proof * proof) contains four
        leading zeros

        :param last_proof: <int> Proof for previous block
        :param proof: <int> Potential proof to be checked
        :return: <bool> True if valid, False otherwise
        """
        guess = '{}{}'.format(last_proof, proof).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'
    #############
    # consensus #
    #############

    def is_valid_chain(self, chain):
        """
        Determine if the passed chain is valid

        :param chain: <list> block chain to test
        :return: <bool> True if valid, otherwise False
        """
        last_block=chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print('{}'.format(last_block))
            print('{}'.format(block))
            print("\n------------\n")
            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.is_valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True


    def resolve_conflicts(self):
        """
        Resolve conflicts in different opinions of blockchain state.
        choose longest chain found in network.

        :return: <bool> True if chain replaced, otherwise False
        """
        all_nodes = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in all_nodes:
            response = requests.get('http://{}/chain'.format(node))
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.is_valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        return False


#########
# Flask #
#########
app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    blockchain.new_transaction(
                sender='0',
                recipient=node_identifier,
                amount=1
            )
    block=blockchain.new_block(proof)

    response = {
                'message': "New block",
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
            }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    request_data = request.get_json()
    print(request_data)
    required = {'sender', 'recipient', 'amount'}
    missing = required - request_data.keys()
    if missing:
        error_message = "Missing values: " + ', '.join(missing)
        return error_message, 400
    index = blockchain.new_transaction(
            request_data['sender'],
            request_data['recipient'],
            request_data['amount'])
    response = {'message': "Transaction will be added to Block {}".format(index)}
    return jsonify(response), 201



@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
                'chain': blockchain.chain,
                'length': len(blockchain.chain)
            }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    request_data = request.get_json()
    nodes = request_data.get('nodes')
    if nodes is None:
        return "Error: please supply a valid list of nodes", 400
    for node in nodes:
        blockchain.register_node(node)
    response = {
            'message': "New nodes added",
            'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
                    'message': "Chain replaced",
                    'new_chain': blockchain.chain
                }
    else:
        response = {
                    'message': "Chain kept",
                    'chain': blockchain.chain
                }
    return jsonify(response), 200



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
