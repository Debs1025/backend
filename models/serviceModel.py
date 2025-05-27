class Service:
    def __init__(self,
                 title=None,
                 description=None,
                 price=0.0,
                 has_steam_press=False,
                 has_dry_clean=False, 
                 has_wash_only=False):
        
        self.title = title
        self.description = description
        self.price = price
        self.has_steam_press = has_steam_press
        self.has_dry_clean = has_dry_clean
        self.has_wash_only = has_wash_only

    def get_total_price(self):
        total = self.price
        if self.has_steam_press:
            total += 95.00
        if self.has_dry_clean:
            total += 80.00  
        if self.has_wash_only:
            total += 100.00
        return total

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'has_steam_press': self.has_steam_press,
            'has_dry_clean': self.has_dry_clean,
            'has_wash_only': self.has_wash_only,
            'total_price': self.get_total_price()
        }