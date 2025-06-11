Usage example:
```
$ python csv_sqlite_loader.py vandalism_ranking.csv vandalism_ranking
``` 

This loads into SQLite the `vandalism_ranking.csv` file into a table called `vandalism_ranking`.

Access the data via shell:
``` 
$ sqlite3 database.db
sqlite> SELECT * FROM vandalism_ranking;
```
