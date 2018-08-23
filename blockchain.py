
class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

    def new_block(self):
        # Adds new block to chain.
        pass

    def new_transaction(self):
        # Adds new transaction to transaction list.
        pass

    @staticmethod
    def hash(block):
        pass

    @property
    def last_block(self):
        pass