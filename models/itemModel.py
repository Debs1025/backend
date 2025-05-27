class TransactionItem:
    def __init__(self, transaction_id=None, item_id=None,
                 quantity=0, price_per_piece=0.0):
        self.transaction_id = transaction_id
        self.item_id = item_id
        self.quantity = quantity
        self.price_per_piece = price_per_piece
        
    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'item_id': self.item_id,
            'quantity': self.quantity,
            'price_per_piece': self.price_per_piece,
            'subtotal': self.get_subtotal()
        }
        
    def get_subtotal(self):
        return self.quantity * self.price_per_piece