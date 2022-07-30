## Stocker
### Description
An infrastructure for financier/developers to code upon for ***advanced stock market analysis***.  
This is version 2 beta, but there's a lot left out. Needs lots of coding to be done. Basically it's inoperable.  

### TODOS
- Write todos
- refactor
- remove old code from version 1
- generate appropriate bash scripts for running different tasks
- generate a bash script to clean-up unneeded files
- operate on unneeded files using `mktemp` and `mktemp -d`.
- Fix and update the README. ***It's still using a lot of parts from version 1***.
  - lots of things have been deprecated...

### Configs
#### PATHS
1. Base: root of the project
2. Stocks Price: `Base` + 'stocks_prices'
3. Stocks Client Type: `Base` + 'client_type_prices'
4. Stocks Shareholders: `Base` + 'shareholders'
5. Stocks Details: `Base` + 'stocks_detail.json'  
   This is a file that stores metadata about the Tickers.
   It's a `json` file with the following structure.
   ```json
   {
     "رمپنا": {
       "index": "67126881188552864",
       "instrument_id": "IRO1MAPN0001",
       "ci_sin": "IRO1MAPN0000",
       "title": "گروه مپنا (سهامي عام) (رمپنا) - بازار اول (تابلوي فرعي) بورس",
       "group_name": "خدمات فني و مهندسي",
       "base_volume": "7009346"
     }
   }
   ```

#### Database
engine: `postgresql`  
psql db name: `stocker`  
psql host: `localhost`
user: **.env.DB_USER**  
password: **.env.DB_PASSWD**

#### setup
You would need **python 3.9**, **pip**, **virtualenv**, **postgres 12**
for running the project. After you have installed the mentioned tools, clone 
the project and navigate to its root, then run the following. **Might ask for root permissions**.
```sh
./init-db.sh
```
This will initiate the database and grant required privileges.  
**Disclaimer: It will delete the database and the tables and roles if they exist**  

Then run this.
```sh
python ./manage.py migrate
```
This will create all defined django tables and run pre-defined migrations.

#### Redis
port: **.env.REDIS_PORT**

#### setup
To install redis instance do the following. **Replace PORT with chosen port**.
```sh
wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make
make test
make install

sudo mkdir /etc/redis
sudo mkdir /var/redis

sudo cp redis.conf /etc/redis/{PORT}.conf
# edit /etc/redis/{PORT}.conf and replace all ports of 6379 with {PORT}

sudo mkdir /var/redis/{PORT}
sudo cp utils/redis_init_script /etc/init.d/redis_{PORT}
# edit /etc/init.d/redis_{PORT} and replace all ports of 6379 with {PORT}
sudo update-rc.d redis_{PORT} defaults
```
Now run the instance by this.
```sh
sudo /etc/init.d/redis_{PORT} start
```
Now your redis instance should be up and running. From now on init.d will start it automatically.

#### Celery
celery_broker_url: redis://127.0.0.1/{PORT}

Run the celery instance with this.
```sh
# navigate to project root
celery -A Stocker worker -l INFO
```

#### Django
Install requirements before doing anything else with this.
```sh
# navigate to project root
pip install -r requirements.txt
```

Run the project using this.
```sh
# navigate to project root
python ./manage.py runserver
```

### Modules
### TSETMC Client
A module used for downloading, scraping and manipulating actual data of stocks from `tsetmc`.
* tsetmc.client.utils
* tsetmc.client.download
* tsetmc.client.Ticker

### TSETMC Client Utils
##### tsctmc.client.utils.StockController
```python
from typing import *
from tsetmc.client.utils import StockController
ctrl = StockController

ctrl.stocks_details()
# returns the dict loaded from `Stocks Details` Json File

stock_details: dict = ctrl.get_details(symbol='رتینا')
stock_details: dict = ctrl.get_details(index='112875043892574')

index: str = ctrl.get_index(symbol='رتینا')
symbol: str = ctrl.get_symbol(index='2875940857549')
all_symbols: List[str] = ctrl.get_all_symbols()
all_indexes: List[str] = ctrl.get_all_indexes()

ctrl.scrape_symbols_and_indexes()
# Scrapes url `TSE_STOCKS_URL` and retrieves and stores
#   only indexes and symbols of Tickers.

ctrl.scrape_metadata(refresh_indexes=False)
# If refresh_indexes is True, it calls ctrl.scrape_symbols_and_indexes first hand.
# It breaks down all the available tickers (by their indexes)
#   to sqrt(len(indexes)) sections, runs a method for each section simultaneously. 
# It iterates over each section and retrieves the required extra metadata for the ticker.
# At last it appends the new retrieved data to the metadata file.
```

##### tsetmc.client.utils.populate_db
This is a method that searches and populates the database based on the available Stocks in files scraped from `tsetmc`
```python
from tsetmc.client.utils import populate_db
populate_db()

# in migrations
Stock = app.get_model('tsetmc.Stock')
populate_db(klass=Stock)
```

##### tsetmc.client.utils.requests_retry_session
This is a method which makes use of `requests.Session`, `requests.adaptors.HTTPAdaptor` and  
`urllib3.Retry` to initiate a valid session with the network.  
**Copied from https://github.com/Glyphack/pytse-client**


### TSCTMC Client Downloader
#### tsetmc.client.downloader.abstract_downloader.AbstractDownloader
This is an abstract class that should be implemented by other downloaders.
Each Downloader must implement the following.
1. attribute `path`: The path that indicates where the downloaded data should be stored.
2. attribute `file_type`: The file type that each data file should be stored as. Can only be csv.  
3. method `get_attr(symbol)`:  
   This method should return the needed attribute for method `download` through the symbol of the ticker.
4. method `download(attr)`:  
   This method should implement how the desired file should be downloaded.  
   The received attr is an identifier to specify the exact url through the related url located in settings.  
   The method should return the raw downloaded data.
5. method `process(result)`:  
   This method should post-process the raw data to be in the desired state to be ready for saving into the file.
   It should return the processed data.
6. method `save(result, path)`:  
   This method should implement how the processed data should be saved.
   It should not return anything.

The pre-implemented methods which should not be implemented are as follows.
1. method `__init__(symbols)`:
   This method should receive a list of symbols or just a symbol and should download the data for each of those.
   If symbols equals 'all', all symbols will be downloaded.
2. method `_download()`:  
   This method uses 10 workers and multiprocessing to download the data.  
   Then processes the downloaded data and stores the data in a file.


#### tsetmc.client.downloader.PriceRecordsDownloader
This is a class that downloads the price records for the specified symbols.  
The data will be stored in `Stocks Price` path.  
The data will be stored in `csv` format.  
The method process converts table headers as follows:
* \<DTYYYYMMDD> -> date
* \<FIRST> -> open
* \<HIGH> -> high
* \<LOW> -> low
* \<LAST> -> close
* \<VOL> -> volume
* \<CLOSE> -> adjClose
* \<OPENINT> -> count
* \<VALUE> -> value

#### tsetmc.client.downloader.ShareholdersDownloader
This is a class that downloads the shareholders data for the specified symbols.  
The data will be stored in `Stocks Shareholders` path.  
The data will be stored in `csv` format.  
The method process converts table headers as follows:
* سهامدار/دارنده -> shareholder
* سهم -> shares
* درصد -> percentage
* تغییر -> change

#### tsetmc.client.downloader.ClientTypeRecordsDownloader
This is a class that downloads the client type data for the specified symbols.  
The data will be stored in `Stocks Client Type` path.  
The data will be stored in `csv` format.  

#### tsetmc.client.downloader.download
This is a function which receives an attribute symbols and will download all available data for them.  
The parameter symbols can be a list or a string of a symbol. If the parameter is 'all' the function will download the data for all symbols.

```python
from tsetmc.client.download import download
download('all')
download('وبملت')
download(['وبملت', 'وبهمن'])
```

### tsetmc.client.Ticker
A representative class for a stock which can be used to manipulate stock's actual file-data.
```python
from typing import *
from tsetmc.client import Ticker

ticker = Ticker(symbol='وبملت')
ticker = Ticker(index='778253364357513')

ticker.index  # 778253364357513
ticker.symbol  # وبملت
ticker.instrument_id  # IRO1BMLT0001
ticker.ci_sin  # IRO1BMLT0007
ticker.title  # بانك ملت (وبملت) - بازار اول (تابلوي اصلي) بورس
ticker.group_name  # بانكها و موسسات اعتباري
ticker.base_volume  # 27842227
ticker.url  # http://tsetmc.com/Loader.aspx?ParTree=151311&i=778253364357513


ticker.history
"""
            date    open    high  ...     volume  count   close
0     2009-02-18  1050.0  1050.0  ...  330851245    800  1050.0
1     2009-02-21  1051.0  1076.0  ...  335334212   6457  1057.0
2     2009-02-22  1065.0  1074.0  ...    8435464    603  1055.0
3     2009-02-23  1066.0  1067.0  ...    8570222    937  1060.0
4     2009-02-25  1061.0  1064.0  ...    7434309    616  1060.0
          ...     ...     ...  ...        ...    ...     ...
2504  2021-03-13  3780.0  3990.0  ...  281339188   9356  3990.0
2505  2021-03-14  4080.0  4150.0  ...  270006098  11100  4020.0
2506  2021-03-15  4020.0  4280.0  ...  362136753  11046  4240.0
2507  2021-03-16  4090.0  4380.0  ...  499852655  13563  4320.0
2508  2021-03-17  4320.0  4380.0  ...  160731993   7213  4330.0
[2509 rows x 9 columns]
"""

ticker.history.columns
"""
Index(['date', 'open', 'high', 'low', 'adjClose', 'value', 'volume', 'count',
       'close'],
      dtype='object')
"""


ticker.client_types
"""
            date  ...  individual_ownership_change
0     2021-03-17  ...                  -41667382.0
1     2021-03-16  ...                 -174441407.0
2     2021-03-15  ...                  -60078346.0
3     2021-03-14  ...                   -6670483.0
4     2021-03-13  ...                   15219234.0
          ...  ...                          ...
2386  2009-02-25  ...                   -1006004.0
2387  2009-02-23  ...                   -1787760.0
2388  2009-02-22  ...                     329969.0
2389  2009-02-21  ...                   35598339.0
2390  2009-02-18  ...                  183679371.0
[2391 rows x 18 columns]
"""

ticker.client_types.columns
"""
Index(['date', 'individual_buy_count', 'corporate_buy_count',
       'individual_sell_count', 'corporate_sell_count', 'individual_buy_vol',
       'corporate_buy_vol', 'individual_sell_vol', 'corporate_sell_vol',
       'individual_buy_value', 'corporate_buy_value', 'individual_sell_value',
       'corporate_sell_value', 'individual_buy_mean_price',
       'individual_sell_mean_price', 'corporate_buy_mean_price',
       'corporate_sell_mean_price', 'individual_ownership_change'],
      dtype='object')
"""

ticker.shareholders
"""
                                   shareholder  ...      change
0                     دولت جمهوري اسلامي ايران  ...         0.0
1            صندوق تامين آتيه كاركنان بانك ملت  ...         0.0
2        صندوق سرمايه گذاري واسطه گري مالي يكم  ...         0.0
3      BFMصندوق سرمايه گذاري.ا.بازارگرداني ملت  ...  66074892.0
4            شركت پتروشيمي فن آوران-سهامي عام-  ...         0.0
5                 شركت گروه مالي ملت-سهام عام-  ...         0.0
6        شركت سرمايه گذاري صباتامين-سهامي عام-  ...         0.0
7                 شركت تعاوني معين آتيه خواهان  ...         0.0
8   شركت گروه توسعه مالي مهرآيندگان-سهامي عام-  ...         0.0
9                 شركت س اتهران س.خ-م ك م ف ع-  ...         0.0
10          شركت س اخراسان رضوي س.خ-م ك م ف ع-  ...         0.0
11                 شركت س افارس س.خ-م ك م ف ع-  ...         0.0
12              شركت س اخوزستان س.خ-م ك م ف ع-  ...         0.0
13                   شركت شيرين عسل-سهامي خاص-  ...         0.0
14      شركت سرمايه گذاري ملي ايران-سهامي عام-  ...         0.0
15               شركت س ااصفهان س.خ-م ك م ف ع-  ...         0.0
[16 rows x 4 columns]
"""

ticker.shareholders.columns
"""
Index(['shareholder', 'shares', 'percentage', 'change'], dtype='object')
"""
```

#### TSETMC Models
* Stock  
   - index: string  
     tsetmc uses this as a unique identifier for stocks
   - symbol: string
   - url: string

* PeriodicTask  
   - stocks: array
        + an array that keeps a list of id(s)
   - name: string (unique)
   - task: string  
        + the pythonic path of user created tasks
   - interval: fk to `django_celery_beat.IntervalSchedule` (null)  
        + IntervalSchedule represents a repeating schedule as e.g. `2 times per day`
   - crontab: fk to `django_celery_beat.CrontabSchedule` (null)  
        + CrontabSchedule represents the linux crontab schedule.  **read further online**
   - clocked: fk to `django_celery_beat.ClockedSchedule` (null)  
        + ClockedSchedule represents a one-time schedule with a dedicated date and time 
   - expires: datetime (null) (default=null)  
        + If the the current date and time has passed this, the task won't run and it will be removed
   - one_off: boolean (default=false)  
        + If true the task will only be run once and then it will be removed  
   - start_time: datetime (null)  
        + If true the task will start to be considered after the current date and time has passed this
   - enabled: boolean (default=true)
        + If true the task will not be considered but will not be removed too
   - last_run_at: datetime (null=true) (default=0)
   - total_run_count: integer (default=0)
   - description: string  
  
  notes:  
    + Between `interval`, `crontab` and `clocked`, one must be set.

* UserTask
  - task: string
  - user: fk to `django.contrib.auth.models.User`

#### TSETMC TASKS
#### tsetmc.tasks.TaskController
This is a Controller class that identifies, filters (per user), runs and cleans the tasks created in tasks_module.
* get_module_task_function
* get_task_functions
* get_date_tasks
* download_tasks_data
* run_tasks
* cleanup

#### tsetmc.all_tasks
This is a module which stores the user hardcoded tasks. Each user must have their own module in this module.  
After the user tasks have been coded by the admin, he must use `UserTask`
from the admin panel to assign the created tasks to the user.
