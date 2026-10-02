# Text review report

Scope: 2,587 `.txt` files in `assets/`; 34,641 prose lines (about 469,000 words) after
removing ids, coordinates, flags and file names. Checked with aspell (en_GB and en_US) and
LanguageTool 6.8 (en-GB), then every candidate was read in context.

## Fixed (in `text_fixes.py`): 455 corrections, 439 patch entries, 321 files

| Kind | Corrections | Examples |
|---|---|---|
| Misspelled ordinary words | 352 | `manouvres`, `scavanging`, `tarrifs`, `retreival`, `priviliges`, `siezed`, `thorugh`, `maintainance`, `miltiary`, `unweildy`, `cluser`, `statment` |
| Place names vs. the nav-map spelling | 9 | `Parsssus`, `Cansn`/`Casnsa`, `Caruthers` (nav map: Carruthers' Circle), `Gallileo`, `Langrange`, `Sagans Lights` |
| Grammar (exact phrases, unambiguous only) | 94 | `I'll back back very shortly`, `exposed from from`, `it's importance`, `an communications array`, `to be spend thinking`, `who no are no longer`, `we're are all`, `anther`, `has ben misused` |

One of these is a real in-game bug rather than just a typo: `passengers.txt` line 19 has
`$amonut`, a misspelled **substitution token** (the other eight uses are `$amount`), so that
email shows the player the literal text "$amonut" instead of a number.

## Left alone because it looks deliberate

* **Rushed/panicked messages:** `ch2_michaelrangsikitphoemails1.txt` ("fo rhelping", "statio nwhen",
  "werea ware"), `wad_sebastianwheeleremail1.txt`, `blr_asterinallasemail1.txt`, and Nick Fourier's lowercase
  voice (`ddf_nickfourieremail3.txt`: "dont", "therse", "its Nick Fourier").
* **A cipher:** `fbl_estragongeorgeemail1.txt` has a +1 letter-shift line ("Bnld ehmc sgd adzbnm" = "Come find the beacon").
* **Radio static:** `smj_hammerhead.txt` ("[garbled] -ngerous").
* **A joke:** `rdc_freddydunning.txt:178` ("Is it projenitators? Progenators? Projenitors?").
* **Dialect and interjections:** `gonna`, `lookin'`, `ain't`, `you was`, `'allo`, `jus'`, `Aaaaah`, `Hmmm`, censored swearing.
* **Variant spellings that are not errors:** `benefitted`, `unmistakeable`, `licenced`, `reenforced`, `moreso`, `protestors`, `despatching`.
* **Invented names:** all `sector_*` names, ship-name lists, and place names that appear on the nav map.

## Needs your decision (not applied)

Unclear what was intended, or it might be an internal id:

* `enceladus_coridoor.txt:5` `name=coridoor`. Looks like a typo, but room names are internal ids
  (`enceladus_cabin`, ...), so changing it could break references.
* `Colombus Colony` (`tgs_milosmithemail.txt:261`), Columbus?
* `Haper Nebula` / `Haper's Tail` (`coop_ambush_2.txt`), `Haphaestus Nebula` (`coop_pirate_hunt.txt:66`), `Kupier` (`sector_carruthers.txt:91`).
* Probably typos but the intended word is a guess: `info_solarpanels.txt:11` ("the Solar  isted on your nav map"),
  `news_bellointervenesatloni.txt:21` ("shipping lanesw, and eilds such power"), `news_constructionshipsarriveatjansky.txt:19`
  ("coarsed in vain"), `news_earthgateishurtingnoone.txt:25` ("will dishearted something"), `news_labouristorture.txt:4` ("torcher"),
  `wap_unionship.txt:64` ("podly outcomes"), `bug_caseycroma.txt:244` ("frictious"), `tah_monaalajwi2.txt:135` ("an extra 20 ound"),
  `jfs_angelareddy.txt:334` ("how do we you plan to that?"), `news_cansaisfree.txt:35` ("much prizes Sarni wines").
* `bcn_johnmilgramemail.txt`: one long email with many slips ("vacing", "1 maller each day", "out aft quarters",
  "through out our gravity"). It might be deliberately sloppy, so none of it was changed.
* **Person-name spelling variants** (opt-in with `--name-variants`; not in `text_fixes.py`): Barunti → Baruti, Bednarki → Bednarski, Bednsarski → Bednarski, Dalce → Dalca, Dialinese → Diwalinese, Diwalanese → Diwalinese, Diwalenese → Diwalinese, Diwaliese → Diwalinese, Herrara → Herrera, Herrara'S → Herrera'S, Howath → Howarth, Intomitable → Indomitable, Ioannau → Ioannou, Janksy → Jansky, Kahnuna → Kanuna, Kovalevski → Kovalevsky, Kovelevsky'S → Kovalevsky'S, Magellian → Magellan, Mahison → Mathison, Masklyne → Maskelyne, Migram → Milgram, Miniki → Minika, Nigell → Nigella, Opik'S → Okpik'S, Parssussian → Parssusian, Parsussian → Parssusian, Parsussians → Parssusians, Qimmik → Qimmiq, Qinqi → Qingqi, Rajapaske → Rajapakse, Rajpakse → Rajapakse, Ramachadran → Ramachandran, Ramora → Remora, Sharmila → Sharmilla, Sirsiti'S → Sirsati'S, Steaphanie → Stephanie, Svannah → Savannah, Voung → Vuong, Xaioli → Xiaoli, Zania → Zaina.
* Name variants I could not resolve: Allistair/Allister, Atalas/Atlas, Bishup/Biskup, Tilisi/Tillisi, Liange/Liang,
  Narelan/Narellan, Carrutheans/Carrutherean/Carrutheran, Altan/Altin.
* **American spellings in British-spelled text** (60 words, a consistency question rather than errors):
  `whiskey` (20), `asshole` (43), `civilization` (10), `judgment` (7), `defense`, `center`, `honor`, `gray`, `traveler`, `skeptical`, ...

## What this does not cover

* Wrong-but-real words that neither checker flags.
* Text that is not in `assets/*.txt` (strings compiled into `ois.exe`).
* Anything the dictionary treats as a valid name or slang word but is actually a typo (about 3,400 unknown words remain
  after the fixes, nearly all names and slang). `scan` lists them all for review.
