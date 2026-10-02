"""Curated corrections for ois_textcheck.py (see README.md in this folder).

Every entry was checked against its context in the game files. Three tiers:
  SPELLING       plain misspellings of ordinary words          -> applied
  PLACES         misspellings of place names whose canonical
                 spelling is on the in-game nav map            -> applied
  NAME_VARIANTS  person-name / demonym spelling variants       -> OPT-IN (--name-variants)
  GRAMMAR        file-scoped exact phrase fixes                -> applied
Names are often deliberate, so nothing about people's names is applied by default.
"""
# Curated corrections. word (lowercase) -> replacement; case is preserved by the applier.
# SPELLING: plain misspellings of ordinary words.
SPELLING = {'manouvres': 'manoeuvres', 'manouvre': 'manoeuvre', 'manouvreability': 'manoeuvrability', 'scavanging': 'scavenging', 'scavanger': 'scavenger', 'tarrifs': 'tariffs', 'retreival': 'retrieval', 'retreive': 'retrieve', 'cluser': 'cluster', 'dilligence': 'diligence', 'priviliges': 'privileges', 'siezed': 'seized', 'thorugh': 'through', 'fertiliy': 'fertility', 'infertiliy': 'infertility', 'maintainance': 'maintenance', 'miltiary': 'military', 'premitted': 'permitted', 'promting': 'prompting', 'reliase': 'realise', 'statment': 'statement', 'thier': 'their', 'waht': 'what', 'whenver': 'whenever', 'unweildy': 'unwieldy', 'afriad': 'afraid', 'abbhorent': 'abhorrent', 'accellerate': 'accelerate', 'accellerated': 'accelerated', 'achivements': 'achievements', 'actaully': 'actually', 'actualy': 'actually', 'actvity': 'activity', 'administartion': 'administration', 'affiars': 'affairs', 'agains': 'against', 'aksed': 'asked', 'alongisde': 'alongside', 'amonut': 'amount', 'anouncement': 'announcement', 'apalling': 'appalling', 'appparently': 'apparently', 'aquire': 'acquire', 'artifically': 'artificially', 'assitance': 'assistance', 'atendees': 'attendees', 'attendnace': 'attendance', 'availablility': 'availability', 'beacuse': 'because', 'beeen': 'been', 'beginnign': 'beginning', 'behond': 'beyond', 'belive': 'believe', 'beter': 'better', 'btter': 'better', 'blunderbus': 'blunderbuss', 'breifly': 'briefly', 'cacophany': 'cacophony', 'caleld': 'called', 'captian': 'captain', 'catpain': 'captain', 'cental': 'central', 'challening': 'challenging', 'circumstnaces': 'circumstances', 'comapnies': 'companies', 'comopared': 'compared', 'condemnded': 'condemned', 'condifential': 'confidential', 'contruction': 'construction', 'conversative': 'conservative', 'coorindates': 'coordinates', 'corageous': 'courageous', 'coridoor': 'corridor', 'crystaline': 'crystalline', 'deterrant': 'deterrent', 'desiged': 'designed', 'detecing': 'detecting', "didn'y": "didn't", 'diplimatic': 'diplomatic', 'disapora': 'diaspora', 'disembowled': 'disembowelled', 'dormatories': 'dormitories', 'echod': 'echoed', 'embelish': 'embellish', 'enviroments': 'environments', 'errosion': 'erosion', 'exected': 'executed', 'exhange': 'exchange', 'existant': 'existent', 'exlusively': 'exclusively', 'explusion': 'expulsion', 'exposive': 'explosive', 'extracirricular': 'extracurricular', 'familar': 'familiar', 'foreceful': 'forceful', 'frought': 'fraught', 'glamourous': 'glamorous', 'govenrment': 'government', 'haemmorhaging': 'haemorrhaging', 'harlmess': 'harmless', 'heirarchy': 'hierarchy', 'hollistic': 'holistic', 'honur': 'honour', 'horrigfying': 'horrifying', 'hospialised': 'hospitalised', 'houseing': 'housing', 'hte': 'the', 'htlp': 'help', 'idiosyncracies': 'idiosyncrasies', 'imporant': 'important', 'imposable': 'impossible', 'impuned': 'impugned', 'inadmissable': 'inadmissible', 'incoing': 'incoming', 'indiciative': 'indicative', 'indisciminately': 'indiscriminately', 'inlcuded': 'included', 'insensify': 'intensify', 'insid': 'inside', 'insterstellar': 'interstellar', 'intersellar': 'interstellar', 'interstallar': 'interstellar', 'institude': 'institute', 'instutition': 'institution', 'insuting': 'insulting', 'intiative': 'initiative', 'invesemtnt': 'investment', 'invidivualistic': 'individualistic', 'invovles': 'involves', 'irresonsibility': 'irresponsibility', 'jepoardised': 'jeopardised', 'jouney': 'journey', 'largley': 'largely', 'lauch': 'launch', 'leaniency': 'leniency', 'legitimtate': 'legitimate', 'licesned': 'licensed', 'lieutennants': 'lieutenants', 'logstics': 'logistics', 'lyphomas': 'lymphomas', 'maessage': 'message', 'messaage': 'message', 'magananimous': 'magnanimous', 'mght': 'might', 'moduels': 'modules', 'nuciance': 'nuisance', 'opportunit': 'opportunity', 'patchd': 'patched', 'permaneny': 'permanently', 'permissable': 'permissible', 'permisson': 'permission', 'politcal': 'political', 'poppoed': 'popped', 'postiions': 'positions', 'preceeded': 'preceded', 'preocuppied': 'preoccupied', 'priarily': 'primarily', 'produciton': 'production', 'proprtions': 'proportions', 'publically': 'publicly', 'puchases': 'purchases', 'purcursor': 'precursor', 'quarrell': 'quarrel', 'racuous': 'raucous', 'raido': 'radio', 'rampat': 'rampant', 'realtions': 'relations', 'reaons': 'reasons', 'recogniseable': 'recognisable', 'reisdents': 'residents', 'rejoing': 'rejoin', 'remians': 'remains', 'repsonsible': 'responsible', 'requrested': 'requested', 'responsibile': 'responsible', 'resportedly': 'reportedly', 'returement': 'retirement', 'saing': 'saying', 'satement': 'statement', 'sayd': 'said', 'scaringly': 'scarily', 'sectino': 'section', 'seemsl': 'seems', 'senitment': 'sentiment', 'shiping': 'shipping', 'sitaution': 'situation', 'situtation': 'situation', 'sketpical': 'sceptical', 'sould': 'souls', 'spoted': 'spotted', 'staiton': 'station', 'stil': 'still', 'striked': 'struck', 'subsribing': 'subscribing', 'suface': 'surface', 'sugests': 'suggests', 'supeiority': 'superiority', 'suppling': 'supplying', 'surived': 'survived', 'suspiciion': 'suspicion', 'sustainance': 'sustenance', 'synthetsise': 'synthesise', 'sytem': 'system', 'taining': 'tainting', 'termporarily': 'temporarily', 'theie': 'their', 'thinkg': 'think', 'throughtout': 'throughout', 'tranport': 'transport', 'unaccaptable': 'unacceptable', 'unaninmous': 'unanimous', 'undertand': 'understand', 'undgoing': 'undergoing', 'unrealiable': 'unreliable', 'ususual': 'unusual', 'veractiy': 'veracity', 'verticel': 'vertical', 'visibilty': 'visibility', 'weild': 'wield', 'weilding': 'wielding', 'weilds': 'wields', 'whcih': 'which', 'wordhole': 'wormhole', 'yesterdy': 'yesterday', 'gues': 'guess', "we'e": "we're", 'ley': 'key', 'absoutely': 'absolutely', 'accoridng': 'according', 'alwyas': 'always', 'calllisto': 'callisto', 'congratuations': 'congratulations', 'foostuffs': 'foodstuffs', 'furhter': 'further', 'gerenous': 'generous', 'harrassment': 'harassment', 'inerviewer': 'interviewer', 'ingocnito': 'incognito', 'offiical': 'official', 'paasenger': 'passenger', 'poliical': 'political', 'reagrdless': 'regardless', 'rubmlings': 'rumblings', 'servies': 'services', 'shoul': 'should', 'snice': 'since', 'unkonwn': 'unknown', 'secreatary': 'secretary', 'emmissions': 'emissions', 'eminenc': 'eminence', 'empre': 'empire', 'genearl': 'general', 'ginat': 'giant', "governer's": "governor's", 'revaeled': 'revealed', 'miliary': 'military', 'miiltary': 'military', 'agircultural': 'agricultural', 'fascinatng': 'fascinating', 'everytime': 'every time', 'excietment': 'excitement', 'thankyou': 'thank you', 'wareheads': 'warheads', 'ahve': 'have', 'failured': 'failure', 'everythig': 'everything', 'extravagences': 'extravagances', 'constols': 'controls', 'beyons': 'beyond', 'ministr': 'minister', 'entirly': 'entirely', 'socailist': 'socialist', 'detah': 'death', 'prood': 'proof', 'motived': 'motives', 'amssive': 'massive', 'cannisters': 'canisters', 'enstatement': 'instatement', 'kil': 'kill', 'arguiung': 'arguing', 'avoidd': 'avoided', 'enerst': 'earnest', 'everywhre': 'everywhere', 'delgates': 'delegates', 'waverforms': 'waveforms', 'everybit': 'every bit', 'psychadelic': 'psychedelic', 'demadning': 'demanding', 'attent': 'attend', 'talkint': 'talking', 'fpr': 'for', 'shant': "shan't"}
# PLACES: misspellings of place names whose canonical spelling is on the in-game nav map
# (Parssus, Cansa, Carruthers' Circle, Galileo, Lagrange, Sagan's Lights ...).
PLACES = {'parsssus': 'parssus', 'cansn': 'cansa', 'casnsa': 'cansa', "caruther's": "carruther's", 'caruthers': 'carruthers', 'gallileo': 'galileo', 'galielans': 'galileans', 'galiliean': 'galilean', 'gallilean': 'galilean', 'langrange': 'lagrange'}
# NAME_VARIANTS: person-name / demonym spelling variants where one spelling is far more common.
# OPT-IN ONLY -- names may be deliberate, so these are never applied by default.
NAME_VARIANTS = {'bednarki': 'bednarski', 'bednsarski': 'bednarski', 'dalce': 'dalca', 'dialinese': 'diwalinese', 'diwalanese': 'diwalinese', 'diwalenese': 'diwalinese', 'diwaliese': 'diwalinese', 'herrara': 'herrera', "herrara's": "herrera's", 'intomitable': 'indomitable', 'janksy': 'jansky', 'kovalevski': 'kovalevsky', "kovelevsky's": "kovalevsky's", 'magellian': 'magellan', 'masklyne': 'maskelyne', 'mahison': 'mathison', 'migram': 'milgram', "opik's": "okpik's", 'qimmik': 'qimmiq', 'qinqi': 'qingqi', 'rajapaske': 'rajapakse', 'rajpakse': 'rajapakse', 'ramachadran': 'ramachandran', 'ramora': 'remora', "sirsiti's": "sirsati's", 'steaphanie': 'stephanie', 'svannah': 'savannah', 'voung': 'vuong', 'xaioli': 'xiaoli', 'miniki': 'minika', 'kahnuna': 'kanuna', 'barunti': 'baruti', 'nigell': 'nigella', 'ioannau': 'ioannou', 'parsussian': 'parssusian', 'parsussians': 'parssusians', 'parssussian': 'parssusian', 'zania': 'zaina', 'howath': 'howarth', 'sharmila': 'sharmilla'}
# files whose text is deliberately garbled / hurried / ciphered: never touched
DELIBERATE = ['blr_asterinallasemail1.txt', 'ch2_michaelrangsikitphoemails1.txt', 'ddf_nickfourieremail3.txt', 'fbl_estragongeorgeemail1.txt', 'smj_hammerhead.txt', 'wad_sebastianwheeleremail1.txt']
# lines that are internal identifiers, not prose
SKIP_FILES = ["enceladus_coridoor.txt"]
# exact multi-word fixes (applied before word fixes)
PHRASES = {
 "The're a trading terminal":"There's a trading terminal",
 "Sagans Lights":"Sagan's Lights",
 "THe ship drifted":"The ship drifted",
}

# GRAMMAR: (file or None for any file, exact old text, new text). Only unambiguous
# fixes; dialect ("you was", "ain't"), emphasis ("really really") and deliberate
# repetition are left alone.
GRAMMAR = [
 ("info_damage.txt","exposed from from the aft","exposed from the aft"),
 ("efe_drazaterroiremail1.txt","I'll back back very shortly","I'll be back very shortly"),
 ("ch1_beaconemails.txt","Now the the planet","Now the planet"),
 ("news_francishaldarinterviewparttwo.txt","some been some comment","some comment"),
 ("news_nomorenewprisonerssaysvang.txt","less to to the authorities","less to the authorities"),
 ("news_svobudracaptainwantedformurder.txt","that that this investigation","that this investigation"),
 ("owi_akihasagawa3.txt","nebulae the the like","nebulae and the like"),
 ("loj_harryvuong.txt","come and and meet","come and meet"),
 ("tga_angelareddy.txt","also a a savvy","also a savvy"),
 ("tga_test1.txt","also a a savvy","also a savvy"),
 ("tjc_avelinademboemail1.txt","been been writing","been writing"),
 ("wig_unknownemail3.txt","any details our our communications","any details of our communications"),
 ("psw_drabbeyforster.txt","kindly you you using","kindly to you using"),
 ("rsh_changyingwu2.txt","again and and I'll","again and I'll"),
 ("rsh_changyingwu4.txt","again and and I'll","again and I'll"),
 ("rsh_maheebadalemail1.txt","unable to to anything","unable to do anything"),
 ("mhn_mahuikangata.txt","for your sake its not","for your sake it's not"),
 ("mhn_mahuikangata.txt","but its too little too late","but it's too little too late"),
 ("news_attackersofproudstillatlarge.txt","so its hardly a surprise","so it's hardly a surprise"),
 ("news_tradersseekgreenerpastures.txt","and its clear that","and it's clear that"),
 ("owi_fernandogutierrez2.txt","but its an oppressive regime","but it's an oppressive regime"),
 ("tsk_ramonafitzloff.txt","only if its straightforward","only if it's straightforward"),
 ("dbc_andreikovac.txt","It's contents are","Its contents are"),
 ("lwf_avelinadembo.txt","it's importance is","its importance is"),
 ("onm_avelinademboemail1.txt","but it's destruction was","but its destruction was"),
 ("shm_sharmillasingh1.txt","It's registration is","Its registration is"),
 ("ssv_victoriamarks.txt","has it's issues","has its issues"),
 ("ch1_nigelbennett.txt","When she get's my message","When she gets my message"),
 ("int_lesliegarbut.txt","Your gonna keep on","You're gonna keep on"),
 ("owi_nyongalexander2.txt","I'm glad your happy","I'm glad you're happy"),
 ("loj_angelareddy3.txt","wait for your to get back","wait for you to get back"),
 ("msa_marisafranck.txt","you're fee","your fee"),
 ("dac_tepurangata.txt","put a in good word","put in a good word"),
 ("tah_monaalajwi1.txt","Just an trader","Just a trader"),
 ("rsh_francisbonsor.txt","jealous of him an Kazuko","jealous of him and Kazuko"),
 ("rsh_francisbonsor4.txt","jealous of him an Kazuko","jealous of him and Kazuko"),
 ("tsb_asha2.txt","an communications array","a communications array"),
 ("news_ulencefederationrejectsempirescalltokillaea.txt","a interstellar judicial body","an interstellar judicial body"),
 ("news_tjc_opedwhysofewanswersfromjansky.txt","as an horrific tragedy","as a horrific tragedy"),
 ("d38_samkasrils.txt","use this warheads","use these warheads"),
 ("bnb_makroberts2.txt","a bit of a trademarks of","a bit of a trademark of"),
 ("news_perfectgetaway.txt","a dozens of patrol ships","dozens of patrol ships"),
 ("news_magellanresearchvesselsavedbypirates.txt","a dichromatic nebulae","a dichromatic nebula"),
 ("news_arepeoplebeingpaidtobefauxviolentprotesters.txt","pose as a disgruntled workers","pose as disgruntled workers"),
 ("wap_lukevhan.txt","but a troopers in my section","but a trooper in my section"),
 ("dsy_drmathison2.txt","they'll answered","they'll answer"),
 ("news_sandbustmakingwaves.txt","people can turned overnight","people can turn overnight"),
 ("rdc_freddydunning.txt","you won't flying without","you won't fly without"),
 ("jfs_angelareddy4.txt","couldn't have do this","couldn't have done this"),
 ("news_securityconcernsindiwalineseprisons.txt","have begin to engulf","have begun to engulf"),
 ("ssr_sofialangemail3.txt","to be spend thinking","to be spent thinking"),
 ("rdc_freddydunning.txt","you're been out there","you've been out there"),
 ("ows_shengxu.txt","those who are tend only","those who tend only"),
 ("scc_mariskahowarthemail1.txt","what you where lead to believe","what you were led to believe"),
 ("news_workersshockedatbrutalmurder.txt","through out Parsuss","throughout Parssus"),
 ("convoyattack2.txt","Our enemies intelligence","Our enemy's intelligence"),
 ("info_dockingandundocking.txt","your ships autopilot","your ship's autopilot"),
 ("scc_amoskleinemail1.txt","our customers privacy","our customers' privacy"),
 ("news_controversialnewlawbanschildrenfromcertainmakeupandclothes.txt","It send a completely","It sends a completely"),
 ("rsh2_callistobarman.txt","Great, thank! You've","Great, thanks! You've"),
 ("ows_shengxu.txt","? Than the Magellan bureaucrat","? Then the Magellan bureaucrat"),
 ("ows_shengxu.txt","? Than the Galilean official","? Then the Galilean official"),
 ("amp_amalynpelle2.txt","anther non-person","another non-person"),
 ("news_tegafollowsleosexamplebanssand.txt","has ben misused","has been misused"),
 ("news_reviewcommunalchildrearingahistory.txt","who no are no longer","who are no longer"),
 ("news_francishaldarinterviewparttwo.txt","where we're are all","where we're all"),
 ("news_giveusbackkadirisaycansans.txt","as he has ever year","as he has every year"),
 ("lfw_lesterfward4.txt","if you every get there","if you ever get there"),
 ("dbc_andreikovac.txt","it will lucrative for you","it will be lucrative for you"),
 ("dbc_andreikovacemail5.txt","I would've have guessed","I would have guessed"),
 ("info_grapplingarms.txt","If have Grappling Arm","If you have a Grappling Arm"),
 ("info_grapplingarms.txt","you've spend several","you've spent several"),
 ("hme_hartemail1.txt","I had flee your vessel","I had to flee your vessel"),
 ("loj_angelareddy.txt","I need see what","I need to see what"),
 ("ddu_kestajonesemail2.txt","or if their full","or if they're full"),
 ("dkc_daphnekolleremail1.txt","it's is no longer","it is no longer"),
 ("dsy_drclarkemathisonemail1.txt","has peaked your interest","has piqued your interest"),
 ("info_parssusunion.txt","one of two major capital shipyard","one of two major capital shipyards"),
 ("news_dysonstrippossible.txt","have release a paper","have released a paper"),
 ("news_rutternotintegasborderssaysgovernment.txt","if you measures from","if you measure from"),
 ("news_ubpcrackdownescalates.txt","continues to operates","continues to operate"),
 ("news_francishaldarinterviewpartone.txt","many citizen can't","many citizens can't"),
 ("dac_tepurangata.txt","is that the it mirrors","is that it mirrors"),
 ("ddu_kestajones.txt","find some where someone","find somewhere someone"),
 ("news_bednarskideployedtomurrindal.txt","The move way well see","The move may well see"),
 ("news_multinationaleffortstocurbprotestsintega.txt","re-enstatement","reinstatement"),
]
