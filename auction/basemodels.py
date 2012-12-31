from django.db import models
from django.utils.translation import ugettext_lazy as _
from polymorphic.polymorphic_model import PolymorphicModel
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

class CurrencyField(models.DecimalField):
    __metaclass__ = models.SubfieldBase
    
    def to_python(self, value):
        try:
            return super(CurrencyField, self).to_python(value=value).quantize(Decimal("0.01"))
        except AttributeError:
            return None

class BaseAuction(PolymorphicModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    active = models.BooleanField(default=False)
    total_bids = models.IntegerField(default=0)
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        app_label = 'auction'
        verbose_name = _('Auction')
        verbose_name_plural = _('Auctions')
    
    def __unicode__(self):
        return self.name

class BaseAuctionLot(PolymorphicModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    active = models.BooleanField(default=False)
    auction = models.ForeignKey('auction.Auction', related_name='lots')
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        app_label = 'auction'
        verbose_name = _('Auction lot')
        verbose_name_plural = _('Auction lots')
    
    def __unicode__(self):
        return self.name

class BaseBidBasket(models.Model):
    """
    This models functions similarly to a shopping cart, except it expects a logged in user.
    """
    user = models.OneToOneField(User)
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        app_label = 'auction'
        verbose_name = _('Bid basket')
        verbose_name_plural = _('Bid baskets')
    
    def add_bid(self, lot, amount):
        from auction.models import BidItem
        self.save()

        item = BidItem.objects.filter(bid_basket=self,
                                      lot=lot)
        if item.exists():
            bid_basket_item = item[0]
            bid_basket_item.amount = amount
            bid_basket_item.save()
        else:
            bid_basket_item = BidItem.objects.create(bid_basket=self,
                                                     lot=lot,
                                                     amount=amount)
        return bid_basket_item
    
    def update_bid(self, bid_basket_item_id, amount):
        """
        Update amount of bid. Delete bid if amount is 0.
        """
        bid_basket_item = self.bids.get(pk=bid_basket_item_id)
        if not bid_basket_item.is_locked():
            if amount == 0:
                bid_basket_item.delete()
            else:
                bid_basket_item.amount = amount
                bid_basket_item.save()
            self.save()
        return bid_basket_item
    
    def delete_bid(self, bid_basket_item_id):
        """
        Delete a single item from bid basket.
        """
        bid_basket_item = self.bids.get(pk=bid_basket_item_id)
        if not bid_basket_item.is_locked():
            bid_basket_item.delete()
        return bid_basket_item
    
    def empty(self):
        """
        Remove all bids from bid basket.
        """
        if self.pk:
            bids = self.bids.all()
            for bid in bids:
                if not bid.is_locked():
                    bid.delete()
    
    def total_bids(self):
        """
        Returns total bids in basket.
        """
        return len(self.bids.all())

class BaseBidItem(models.Model):
    """
    This is a holder for total number of bids and a pointer to
    item being bid on.
    """

    bid_basket = models.ForeignKey('auction.BidBasket', related_name='bids')
    lot = models.ForeignKey('auction.Lot')
    amount = CurrencyField(max_digits=100, decimal_places=2, null=True, blank=True)

    class Meta:
        abstract = True
        app_label = 'auction'
        verbose_name = _('Bid item')
        verbose_name_plural = _('Bid items')
    
    def is_locked(self):
        if self.lot.auction.end_date <= timezone.now():
            return True
        return False