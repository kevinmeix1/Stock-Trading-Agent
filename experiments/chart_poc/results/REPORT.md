# Chart-PoC: historischer Vergleichsbericht

Reale eingefrorene Tagesdaten: AAPL, IBM und MSFT, 01.03.2000–01.03.2013. Historische Fallstudie, keine aktuelle Marktanalyse.

## Ergebnis

**Ein belastbarer Vorteil von MASS gegenüber beiden einfachen Trend-/Momentumverfahren ist in diesem Holdout nicht nachgewiesen.**
Drei korrelierte, überlebende US-Technologietitel erlauben keine belastbare allgemeine Aussage über andere Aktien, Sektoren oder heutige Märkte.

| Phase | Prognosen / gemeinsame Termine | MASS | Trend SMA20/50 | Momentum20 | Immer positiv |
|---|---:|---:|---:|---:|---:|
| validation | 111 / 37 | 45.95% | 59.46% | 60.36% | 61.26% |
| holdout | 117 / 39 | 47.86% | 47.86% | 46.15% | 58.12% |

Primärmetrik: korrekte Richtung der tatsächlichen 20-Bar-Logrendite ab dem bekannten Schlusskurs. Neutral-/Nullfälle zählen 0,5. Das sind Prognosequoten, keine Handelsrenditen.

## Gepaarte Holdout-Unterschiede

| MASS minus | Unterschied in Prozentpunkten | Intervall |
|---|---:|---|
| trend | +0.00 | [-15.38; +14.53] |
| momentum | +1.71 | [-10.26; +11.97] |

97,5%-Intervalle pro Vergleich, Bonferroni für zwei primäre Vergleiche; approximativer Moving-Block-Bootstrap über gemeinsame Termine, Blocklänge 5, 5.000 Wiederholungen, Seed 20261108. Aktien werden innerhalb jedes Datums gemeinsam gehalten. Rohprognosen sind keine unabhängigen Beobachtungen. Intervalle bedingen auf die fixe Trainingsbibliothek; sie erfassen keine Universums- oder Trainingsauswahlunsicherheit.

## Einzelreihen im Holdout

| Symbol | MASS | Trend | Momentum |
|---|---:|---:|---:|
| AAPL | 38.46% | 48.72% | 56.41% |
| IBM | 61.54% | 43.59% | 43.59% |
| MSFT | 43.59% | 51.28% | 38.46% |

## Bestätigte Marktstrukturen und Double Bottoms

Pivots werden erst zwei abgeschlossene Bars nach ihrem Extrem bekannt. HH/HL/LH/LL vergleichen aufeinanderfolgende bestätigte Extrema desselben Typs. Gleichstände erhalten EH/EL; Outside-Bar-Doppelpivots werden als mehrdeutig ausgelassen. Alle Ereignisse stehen in structures.json.

| Symbol | Bestätigte Swings | Double Bottoms | Reife 20-Bar-Fälle | Davon negative Folge | Schlusskurs-Invalidierung binnen 20 Bars |
|---|---:|---:|---:|---:|---:|
| AAPL | 853 | 6 | 6 | 2 | 0 |
| IBM | 843 | 5 | 5 | 1 | 0 |
| MSFT | 863 | 4 | 4 | 3 | 1 |

Die Patternzählung umfasst den gesamten Datensatz einschließlich Training. Sie misst algorithmische Erkennung und beobachteten Verlauf, keine unabhängig annotierte Erkennungspräzision. Der MASS-Vergleich nutzt alle vorab geplanten Termine und ist nicht auf seltene Double Bottoms beschränkt.

### Letzte drei bestätigte Swings je Reihe

| Symbol | Pivotdatum | Erst bekannt am | Struktur | Preis in adjustierten Snapshot-USD |
|---|---|---|---|---:|
| AAPL | 2013-02-11 | 2013-02-13 | HH | 63.2408 |
| AAPL | 2013-02-25 | 2013-02-27 | LH | 59.3519 |
| AAPL | 2013-02-26 | 2013-02-28 | LL | 57.0750 |
| IBM | 2013-02-12 | 2013-02-14 | HL | 171.9110 |
| IBM | 2013-02-19 | 2013-02-21 | LH | 174.3901 |
| IBM | 2013-02-25 | 2013-02-27 | LL | 170.6067 |
| MSFT | 2013-02-21 | 2013-02-25 | HL | 24.0485 |
| MSFT | 2013-02-25 | 2013-02-27 | LH | 24.7727 |
| MSFT | 2013-02-27 | 2013-03-01 | HL | 24.1368 |

### Sämtliche bestätigten Double Bottoms und beobachtete Folge

Die Preise sind rückwirkend adjustierte Snapshot-Einheiten, keine damaligen handelbaren Kurse. Negative Folgen bleiben aufgeführt.

| Symbol | Erstes / zweites Tief | Close-Bestätigung | Nackenlinie adjustiert | Tatsächliche 20-Bar-Folge | Invalidierung binnen 20 Bars |
|---|---|---|---:|---:|---|
| AAPL | 2001-11-29 / 2001-12-14 | 2002-01-31 | 1.5441 | -5.14% | nein |
| AAPL | 2008-02-07 / 2008-02-26 | 2008-03-18 | 16.8353 | +15.72% | nein |
| AAPL | 2009-06-23 / 2009-07-08 | 2009-07-15 | 18.5908 | +12.55% | nein |
| AAPL | 2009-10-19 / 2009-11-02 | 2009-12-28 | 26.8221 | -1.76% | nein |
| AAPL | 2011-08-08 / 2011-08-22 | 2011-08-29 | 49.4740 | +2.38% | nein |
| AAPL | 2012-06-12 / 2012-06-28 | 2012-07-02 | 75.8232 | +3.08% | nein |
| IBM | 2003-10-23 / 2003-11-06 | 2003-11-13 | 68.1943 | +1.78% | nein |
| IBM | 2003-11-06 / 2003-11-21 | 2003-12-10 | 68.7977 | -0.57% | nein |
| IBM | 2008-03-14 / 2008-03-31 | 2008-04-16 | 94.5412 | +6.28% | nein |
| IBM | 2008-12-12 / 2008-12-29 | 2009-01-06 | 69.8284 | +4.03% | nein |
| IBM | 2011-12-21 / 2012-01-09 | 2012-01-23 | 159.6168 | +2.19% | nein |
| MSFT | 2001-03-21 / 2001-04-04 | 2001-04-10 | 19.4914 | +17.96% | nein |
| MSFT | 2003-02-11 / 2003-02-27 | 2003-03-17 | 16.6356 | -4.51% | nein |
| MSFT | 2003-12-22 / 2004-01-13 | 2004-01-26 | 19.1254 | -6.67% | ja |
| MSFT | 2012-11-16 / 2012-12-05 | 2013-01-25 | 24.3259 | -1.02% | nein |

## Nachvollziehbare Fehlinterpretationen

Auswahlregel: die drei größten absoluten Prognosefehler im Holdout, bei denen MASS eine positive Folge erwartet und die tatsächliche Folge negativ ist. Vollständige Treffer und Gegenbeispiele bleiben in predictions.json und predictions.csv enthalten.

### AAPL – 2013-01-10

60-Bar-Query ab 2012-10-12; erwarteter geometrischer 20-Bar-Verlauf +8.74%, tatsächlich bis 2013-02-08 -8.76%. Ähnliche Vergangenheit hat hier die Richtung verfehlt.

| Historisches Fenster | Outcome bis | MASS-Distanz | Tatsächliche historische Folge |
|---|---|---:|---:|
| 2002-05-24–2002-08-19 | 2002-09-17 | 2.9349 | -7.38% |
| 2006-01-10–2006-04-05 | 2006-05-04 | 3.5006 | +5.83% |
| 2000-03-21–2000-06-14 | 2000-07-13 | 4.3825 | +24.94% |
| 2001-06-28–2001-09-27 | 2001-10-25 | 4.5581 | +23.73% |
| 2000-09-12–2000-12-05 | 2001-01-04 | 4.7840 | +0.35% |

### MSFT – 2010-05-27

60-Bar-Query ab 2010-03-04; erwarteter geometrischer 20-Bar-Verlauf +10.46%, tatsächlich bis 2010-06-25 -5.64%. Ähnliche Vergangenheit hat hier die Richtung verfehlt.

| Historisches Fenster | Outcome bis | MASS-Distanz | Tatsächliche historische Folge |
|---|---|---:|---:|
| 2006-02-09–2006-05-05 | 2006-06-05 | 4.2744 | -5.09% |
| 2000-09-29–2000-12-22 | 2001-01-24 | 4.5305 | +35.53% |
| 2002-05-02–2002-07-26 | 2002-08-23 | 4.5308 | +15.15% |
| 2001-11-15–2002-02-12 | 2002-03-13 | 4.6495 | +3.26% |
| 2003-08-26–2003-11-18 | 2003-12-17 | 4.8763 | +7.51% |

### AAPL – 2011-10-28

60-Bar-Query ab 2011-08-05; erwarteter geometrischer 20-Bar-Verlauf +8.06%, tatsächlich bis 2011-11-28 -7.12%. Ähnliche Vergangenheit hat hier die Richtung verfehlt.

| Historisches Fenster | Outcome bis | MASS-Distanz | Tatsächliche historische Folge |
|---|---|---:|---:|
| 2006-08-15–2006-11-07 | 2006-12-06 | 4.8935 | +11.58% |
| 2004-05-06–2004-08-02 | 2004-08-30 | 5.0935 | +8.04% |
| 2005-08-10–2005-11-02 | 2005-12-01 | 5.4633 | +19.43% |
| 2005-01-07–2005-04-05 | 2005-05-03 | 5.4772 | -13.56% |
| 2001-10-22–2002-01-16 | 2002-02-14 | 5.4807 | +18.38% |

## Methodik und Grenzen

- Parameter wurden vor der ersten Ergebnisauswertung in protocol.json und einem eigenen Git-Commit fixiert; kein Tuning auf Validation oder Holdout.
- Training endet 2006; Validation 2007–2009, Holdout 2010–2013. Alle fünf historischen Matches eines Queries stammen aus der festen Trainingsbibliothek, ihre vollständige 20-Bar-Folge endet zusätzlich vor Beginn des Queries. Feature- und Outcome-Intervalle der fünf Nachbarn überlappen sich nicht.
- MASS vergleicht 60 logarithmierte Adjusted-Close-Werte mit Z-Normalisierung je Fenster (Populationsstandardabweichung, ddof=0). Kein DTW, keine Zeitdehnung, kein gelerntes Embedding. Formähnlichkeit beseitigt Preisniveau und Amplitude und garantiert keinen ähnlichen Folgepfad.
- Trend: Vorzeichen SMA20 minus SMA50; Momentum: Vorzeichen der letzten 20-Bar-Rendite. Gleiche Query-/Outcome-Termine und dieselben verfügbaren 60 Bars. Immer-positiv kontrolliert den Markt-/Klassenbias.
- 20-Bar-Abstand verhindert sich überlappende Zielrenditeintervalle; die 60-Bar-Features bleiben überlappend. Die Blocklängen 3 und 8 werden unverändert als Sensitivität in summary.json ausgewiesen.
- Snapshot-OHLC werden mit adj_close/close skaliert. Dies ist eine rückwirkend adjustierte Quelle einschließlich späterer Kapitalmaßnahmen, kein historischer Point-in-time-Feed. Z-normalisierte Preisformen und ATR-Verhältnisse sind invariant gegen einen gemeinsamen positiven Skalierungsfaktor; exakte damalige handelbare Preislevels werden nicht behauptet.
- Keine unabhängigen menschlichen Patternlabels, keine Aussage über verpasste Formationen oder wissenschaftlich kalibrierte Wahrscheinlichkeiten.
- Keine Gebühren-/Slippage- oder Ausführungssimulation: verglichen werden Folgeprognosen, keine Handelsentscheidungen oder Strategierenditen.
- Bestehende P0-Probleme (RSI, künstliche Fundamentaldaten, übersteuerbare Regeln) wurden nicht verändert. Der PoC importiert keine Anwendungsmodule und benötigt keine KI-, TradingView- oder Brokerverbindung.

Datenherkunft, Lizenzerklärung und SHA-256: data/manifest.json und DATA_NOTICE.md. Regeln und Reproduktionsbefehle: README.md.

Protokoll-SHA-256 (kanonisches JSON): c6f7d05ce631241a86988fbe1dcd379c7ba310d1dd3510de96217a1df928f31d
Datensnapshot-Manifest-SHA-256 (kanonisches JSON): 52c6e8dfaef80271e5826ce8a7fcde4a88fd2db1372f690a6c6eb3f695d3d132
