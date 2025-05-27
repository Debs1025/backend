import datetime

class Transaction:
    def __init__(self, 
                 user_id=None, 
                 shop_id=None,
                 service_name=None,
                 kilo_amount=0.0,
                 subtotal=0.0,
                 delivery_fee=30.0,
                 voucher_discount=0.0,
                 delivery_address=None,
                 payment_method='Cash on Delivery',
                 scheduled_date=None,  
                 scheduled_time=None, 
                 notes=None,
                 items=None):
        # Required fields
        self.user_id = user_id
        self.shop_id = shop_id
        self.service_name = service_name
        self.kilo_amount = kilo_amount
        self.subtotal = subtotal
        self.scheduled_date = scheduled_date
        self.scheduled_time = scheduled_time

        # Optional fields with defaults
        self.delivery_fee = delivery_fee
        self.voucher_discount = voucher_discount
        self.delivery_address = delivery_address
        self.payment_method = payment_method
        self.notes = notes
        self.items = items if items is not None else {}

        # Status fields
        self.status = 'Pending'
        self.payment_status = 'Pending'

    def to_dict(self):
        self.validate()
        # Format scheduled_date
        if isinstance(self.scheduled_date, (datetime.datetime, datetime.date)):
            scheduled_date_str = self.scheduled_date.strftime('%Y-%m-%d')
        else:
            scheduled_date_str = str(self.scheduled_date)
        # Format scheduled_time
        if isinstance(self.scheduled_time, (datetime.datetime, datetime.time)):
            scheduled_time_str = self.scheduled_time.strftime('%H:%M:%S')
        elif isinstance(self.scheduled_time, datetime.timedelta):
            total_seconds = int(self.scheduled_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            scheduled_time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        else:
            scheduled_time_str = str(self.scheduled_time)

        return {
            'user_id': self.user_id,
            'shop_id': self.shop_id,
            'service_name': self.service_name,
            'kilo_amount': self.kilo_amount,
            'subtotal': self.subtotal,
            'delivery_fee': self.delivery_fee,
            'voucher_discount': self.voucher_discount,
            'delivery_address': self.delivery_address,
            'payment_method': self.payment_method,
            'scheduled_date': scheduled_date_str,
            'scheduled_time': scheduled_time_str,
             'notes': self.notes,
            'items': self.items,
            'total_amount': self.get_total(),
            'status': self.status,
            'payment_status': self.payment_status
        }

    def get_total(self):
        return self.subtotal + self.delivery_fee - self.voucher_discount