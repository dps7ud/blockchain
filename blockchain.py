import hashlib
import json

from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request



class Blockchain(object):
    ##############
    # definition #
    ##############
    def __init__(self):
        self.current_transactions = []
        self.chain = []

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
                'transactions': block{'transactions'],
                'proof': block['proof']
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
                'length': len(blockchain.chian)
            }
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
