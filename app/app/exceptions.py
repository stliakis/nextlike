class ItemNotFound(Exception):
    def __init__(self, collection, item_id):
        self.collection = collection
        self.item_id = item_id
