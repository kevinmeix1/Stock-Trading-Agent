# Herkunft und eingefrorene Daten

Die Dateien AAPL.csv, IBM.csv und MSFT.csv enthalten reale historische Tageskurse, keine Simulation.

- Primärdaten: Quandl WIKI Prices.
- Archiv: [marketneutral / Quandl WIKI US Equities, Version 1](https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites/versions/1).
- Bezugsquelle: [Bokeh sampledata, Commit c0ccb5facf6db1c2ee4dffdde80ad9c06bc9b587](https://github.com/bokeh/bokeh_sampledata/tree/c0ccb5facf6db1c2ee4dffdde80ad9c06bc9b587).
- Datenlizenz laut [dataset-spezifischem Bokeh-Verzeichnis](https://github.com/bokeh/bokeh_sampledata/blob/c0ccb5facf6db1c2ee4dffdde80ad9c06bc9b587/licenses/datasets.json): **Public Domain**; dort ist der archivierte Quandl-Publisherhinweis zur Weitergabe verzeichnet. Die BSD-Lizenz der Bokeh-Software wird nicht als Lizenz aller Datensätze ausgegeben.
- [Quellmodul mit Angaben zu Adjustment und Ursprung](https://github.com/bokeh/bokeh_sampledata/blob/c0ccb5facf6db1c2ee4dffdde80ad9c06bc9b587/src/bokeh_sampledata/stocks.py).

Der SHA-256 des bezogenen gzip-Archivs ist `5abadf99b2d394f920120a27de6f0df129859d71d4cfb0bf661bcc99446ab1fd`. Der Beschaffer extrahiert ausschließlich die drei vorab gewählten Titel, benennt CSV-Spalten in Kleinbuchstaben um und schreibt deterministische LF-Zeilenenden. Es werden keine Preise interpoliert, aufgefüllt oder erfunden. Einzelne Datei-Hashes und exakte Zeiträume stehen im [Manifest](data/manifest.json).

Open/High/Low/Close und Volumen sind in den gespeicherten CSVs unadjustiert. `adj_close` stammt unverändert aus dem archivierten Datensatz und enthält Split-/Dividendenanpassungen einschließlich späterer Kapitalmaßnahmen. Die Analyse skaliert je Zeile OHLC mit `adj_close/close`. Volumen bleibt roh und geht nicht in Matching oder Baselines ein. Die Transformation vermeidet rohe Split-Sprünge, ersetzt jedoch kein Point-in-time-Datenarchiv.

Die Handelstage sind als US-Sessiondatum ohne Uhrzeit gespeichert. Alle drei Reihen müssen dieselben Daten enthalten; die Analyse führt weder implizite Zeitverschiebung noch Forward-Fill aus. Die Quelle endet 2013; die Ergebnisse sind eine historische Methodenprüfung und keine aktuelle Bewertung dieser Aktien.
