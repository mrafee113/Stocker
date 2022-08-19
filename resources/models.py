from django.db import models
from django.db.models import Max, Count
from django.core.validators import MinValueValidator, MaxValueValidator


class IndustryGroup(models.Model):
    name = models.CharField(max_length=200)


class Institution(models.Model):
    name = models.CharField(max_length=200)


class Director(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    position = models.CharField(max_length=100)  # todo: add choices


class ShareHolder(models.Model):
    shareholder_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=300)


# todo: add complex field validation
# todo: add __repr__ and __str__
class Company(models.Model):
    tsetmc_index = models.CharField(
        blank=True, max_length=30,
        help_text='TSETMC uses this id as a unique identifier for stocks.')
    tsetmc_old_indexes = models.JSONField(default=list)  # todo: convert to pslq.ArrayField
    tsetmc_symbol = models.CharField(blank=True, max_length=50)
    codal_symbol = models.CharField(blank=True, max_length=50)
    mycodal_id = models.CharField(
        blank=True, max_length=10,
        help_text="mycodal_id is an id that mycodal.ir uses as a unique identifier for companies.")

    tsetmc_url = models.URLField(null=True, blank=True, max_length=500)
    codal_url = models.URLField(null=True, blank=True, max_length=500)  # fixme: does not validate url
    codal_documents_url = models.URLField(null=True, blank=True, max_length=500)
    mycodal_url = models.URLField(null=True, blank=True, max_length=500)
    mycodal_documents_url = models.URLField(null=True, blank=True, max_length=500)

    name = models.CharField(blank=True, max_length=200)
    tsetmc_title = models.CharField(blank=True, max_length=500)
    isin = models.CharField(
        blank=True, max_length=30, help_text="codal.ISIN is the same as tsetmc.Instrument_id")

    @property
    def instrument_id(self) -> str:
        return self.isin

    isic = models.CharField(
        blank=True, max_length=30,
        help_text="codal.ISIC is one of the ids codal.ir uses as a unique identifier for companies.")
    ci_sin = models.CharField(blank=True, max_length=30, verbose_name='ci_sin',
                              help_text="tsetmc uses this id to store shareholders information.")
    tsetmc_industry_group = models.ForeignKey(IndustryGroup, on_delete=models.SET_NULL, null=True,
                                              related_name='tsetmc_companies', related_query_name='tsetmc_companies')
    mycodal_industry_group = models.ForeignKey(IndustryGroup, on_delete=models.SET_NULL, null=True,
                                               related_name='mycodal_companies', related_query_name='mycodal_companies')
    company_type = models.CharField(blank=True, max_length=200)  # todo: add choices
    essence = models.CharField(blank=True, max_length=200)  # todo: add choices
    acceptance_type = models.CharField(blank=True, max_length=200)  # todo: add choices
    website = models.URLField(null=True, blank=True, max_length=500)
    board_of_directors = models.ManyToManyField(Director, blank=True, symmetrical=False)
    similar_companies = models.ManyToManyField("self", blank=True, symmetrical=False)
    base_volume = models.PositiveIntegerField(default=0)
    registered_capital = models.PositiveBigIntegerField(default=0)
    unregistered_capital = models.PositiveBigIntegerField(default=0)
    shareholders = models.ManyToManyField(
        ShareHolder, through='TickerShare', symmetrical=False, through_fields=('company', 'shareholder'))

    documents_last_updated = models.DateTimeField(null=True, default=None)
    last_updated = models.DateTimeField(auto_now_add=True)

    financial_end_of_year_month = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)])
    financial_end_of_year_day = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])

    tsetmc_overview_title = models.CharField(max_length=200)
    tsetmc_market_explanation = models.CharField(max_length=200)

    @classmethod
    def locate_duplicates(cls, *field_names):
        if not field_names:
            return

        return cls.objects.values(*field_names).order_by(). \
            annotate(max_id=Max('id'), count_id=Count('id')). \
            filter(count_id__gt=1)

    # todo: create mixin class
    #  maybe even a django utility mixin project sometime...
    @classmethod
    def delete_duplicates(cls, *field_names):
        if not field_names:
            return
        duplicates = cls.locate_duplicates(*field_names)
        for duplicate in duplicates:
            cls.objects.filter(
                **{x: duplicate[x] for x in field_names}
            ).exclude(id=duplicate['max_id']). \
                delete()


class TickerShare(models.Model):
    shareholder = models.ForeignKey(ShareHolder, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    number_of_shares = models.PositiveBigIntegerField()
    shares_percentage = models.DecimalField(max_digits=4, decimal_places=2)
    change = models.BigIntegerField(default=0)
    # todo: add history revisioning. find it from miare.
    # todo: or add datetime and a method to find...
    #  locate logic from miare


class TickerPrice(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    open = models.PositiveIntegerField()
    high = models.PositiveIntegerField()
    low = models.PositiveIntegerField()
    adj_close = models.PositiveIntegerField()
    value = models.PositiveBigIntegerField()
    volume = models.PositiveBigIntegerField()
    count = models.PositiveIntegerField()
    close = models.PositiveIntegerField()

    class Meta:
        unique_together = ('company', 'date')


class CorporateIndividualEntry(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()

    individual_buy_count = models.PositiveIntegerField(null=True, blank=True)
    corporate_buy_count = models.PositiveIntegerField(null=True, blank=True)
    individual_sell_count = models.PositiveIntegerField(null=True, blank=True)
    corporate_sell_count = models.PositiveIntegerField(null=True, blank=True)

    individual_buy_volume = models.PositiveBigIntegerField(null=True, blank=True)
    corporate_buy_volume = models.PositiveBigIntegerField(null=True, blank=True)
    individual_sell_volume = models.PositiveBigIntegerField(null=True, blank=True)
    corporate_sell_volume = models.PositiveBigIntegerField(null=True, blank=True)

    individual_buy_value = models.PositiveBigIntegerField(null=True, blank=True)
    corporate_buy_value = models.PositiveBigIntegerField(null=True, blank=True)
    individual_sell_value = models.PositiveBigIntegerField(null=True, blank=True)
    corporate_sell_value = models.PositiveBigIntegerField(null=True, blank=True)

    individual_buy_avg = models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=2)
    corporate_buy_avg = models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=2)
    individual_sell_avg = models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=2)
    corporate_sell_avg = models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=2)

    ownership_change: int = models.BigIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('company', 'date')


class PriceModification(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    prev_price = models.IntegerField()
    next_price = models.IntegerField()

    class Meta:
        unique_together = ('company', 'date')


class CapitalIncrease(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField()
    prev_stocks = models.BigIntegerField()
    next_stocks = models.BigIntegerField()

    class Meta:
        unique_together = ('company', 'date')


class DPS(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    issuance_date = models.DateField()
    assembly_date = models.DateField()
    fiscal_date = models.DateField()
    dividends = models.BigIntegerField()
    dps = models.IntegerField()


class SupervisorMessage(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    datetime = models.DateTimeField()
    title = models.CharField(max_length=200)
    message = models.TextField()
