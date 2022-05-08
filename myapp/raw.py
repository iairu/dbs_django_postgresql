from django.db import connections


def _dict_fetch_one(cursor): 
    # z Django docs https://docs.djangoproject.com/en/4.0/topics/db/sql/#executing-custom-sql-directly
    columns = [col[0] for col in cursor.description]
    # return [dict(zip(columns, row)) for row in cursor.fetchall()] # povodne: vsetky zaznamy
    # return dict(zip(columns, (cursor.fetchone(), cursor.fetchone()))) # dva zaznamy
    return dict(zip(columns, (cursor.fetchone()))) # jeden zaznam

def _dict_fetch_all(cursor): 
    # z Django docs https://docs.djangoproject.com/en/4.0/topics/db/sql/#executing-custom-sql-directly
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()] # povodne: vsetky zaznamy

# Create your models here.
def sql_query_one(cursor_query: str): 
    # z Django docs https://docs.djangoproject.com/en/4.0/topics/db/sql/#executing-custom-sql-directly
    # treba opatrne s SQL, pretoze sa nad nim robia nejake upravy (napr. neukoncuje sa s ;), vid dokumentaciu
    with connections['readonly'].cursor() as cursor:
        cursor.execute(cursor_query)
        out = _dict_fetch_one(cursor)
    return out

def sql_query_all(cursor_query: str): 
    # z Django docs https://docs.djangoproject.com/en/4.0/topics/db/sql/#executing-custom-sql-directly
    # treba opatrne s SQL, pretoze sa nad nim robia nejake upravy (napr. neukoncuje sa s ;), vid dokumentaciu
    with connections['readonly'].cursor() as cursor:
        cursor.execute(cursor_query)
        out = _dict_fetch_all(cursor)
    return out

# priklad pouzitia: aggregate(a, "patch_version", "matches", ["match_id", "duration"])
def aggregate(l: list[dict], key, new_group, will_group: list[str]):
    # ocakava sa na vstupe zoradeny obsah listu na zaklade key, kedze kluce spaja v poradi vyskytu
    # a znamena aggregated
    a_keyval = None
    a_entry: dict = {}
    a_list: list[dict] = []
    for d in l:
        if (d[key] == a_keyval): # Ak sa jedna o rovnaku hodnotu kluca
            # Pridanie casti na agregovanie z tohto riadku k existujucej agregacii
            tmp = {}
            for i, x in enumerate(will_group):
                tmp[x] = d[will_group[i]]
            # Kontrola ze ci v danej casti vobec su nejake hodnoty (teda ak obsahuje len null -> nepridat)
            if not all(value == None for value in tmp.values()):
                a_entry[new_group].append(tmp)
        else: # Ak sa jedna o novu hodnotu kluca
            if (a_keyval != None): a_list.append(a_entry) # Ak uz bola agregacia, treba ju ulozit
            a_keyval = d[key] # Nova hodnota kluca
            a_entry = d # Nova agregacia k tomuto prvku (prvy vyskyt)
            # Agregacia samotneho prveho prvku
            a_entry[new_group] = []
            tmp = {}
            for i, x in enumerate(will_group):
                tmp[x] = d[will_group[i]]
            if not all(value == None for value in tmp.values()):
                a_entry[new_group].append(tmp)
            for x in will_group: a_entry.pop(x) # Odobranie povodnej formy uz agregovanych casti
    if (a_keyval != None): a_list.append(a_entry) # Treba ulozit poslednu agregaciu
    return a_list # Navrat "agregovanych" "de-duplikovanych" prvkov
    
# priklad pouzitia: constrained_max(a, "hero_id", "winner", "count", ["ability_id", "ability_name", "hero_name"])
def constrained_max(l: list[dict], group_key, constrain_key, max_key, extract_keys = []):
    # max_key definuje, z ktoreho stlpca sa ponecha len najvacsia najdena hodnota pre
    # rozdielne najdene hodnoty constrain_key, pricom toto sa vykona separatne pre kazdy
    # rozdielny group key
    # navrh struktury: mpc[group] = {constrain_found_value: row_with_max, ...}
    # povodne som sa pokusil o riesenie tohto cez SQL ale prislo mi to prilis komplexne
    # s potrebnostou viacerych vnorenych SELECTov, potreba row merge, menej prehladne zoskupovanie v GROUP BY na rozdiel od jedneho kluca tu, ...
    mpc = list() # max_per_constrain[group_value]
    for d in l: # d => row ako dictionary
        # group_key: najdi / inicializuj dict pre group vo vysledku
        mpc_group = None
        # skus najst
        for g in mpc: 
            if (g[group_key] == d[group_key]): 
                mpc_group = g
                break
        # inicializacia ak nenajdena
        if (mpc_group == None): 
            mpc_group = dict()
            mpc_group[group_key] = d[group_key]
            mpc.append(mpc_group) # toto je len link, nie kopia (mpc_group je dalej pouzity ako odkaz)
        # inicializacia s prvou hodnotou / vymena s dalsou vacsou az eventuelne max
        if ((not d[constrain_key] in mpc_group) or (d[max_key] > mpc_group[d[constrain_key]][max_key])):
            for extract_key in extract_keys: # vytiahni vsetky hodnoty na extrahovanie mimo constrain o uroven vyssie
                # je to ako keby opak agregacie, ocakava sa ze hodnoty su zamenitelne za group_key, ale ak niesu
                # tak sa pouziju jednoducho tie relevantne pre najdene maximum, avsak v takom pripade nie je implementovane
                # rozlisenie medzi constrain_keys a teda hodnota najdena u maxima posledneho constrain_key vyhrava
                mpc_group[extract_key] = d[extract_key]
                del d[extract_key] # nasledne hodnoty odstran z riadku, lebo nema zmysel ich davat do urovne nizsie
            mpc_group[d[constrain_key]] = d # nastav obsah constrain dictu na cely zvysok riadku
            del d[constrain_key] # odstran constrain_key z hodnot riadku, pretoze jeho rozdielne hodnoty uz su
            # pouzite ako agregatory (constrainy) resp. extrahovane na vyssiu uroven, takze nie je dovod uchovavat
            del d[group_key] # podobne, odstran group_key, pretoze uz bol extrahovany na vyssiu uroven
            # a nie je dovod ho uchovavat duplicitne aj na tejto urovni
    return mpc

# kvoli kapitalizacii hodnot ako True, False a jej zmene na lowercase pri konverzii na json
# tato funkcia taktiez pred porovnanim s keys_before zmeni ostatne keys na lowercase => pouzit lowercase v keys_before
# ponechal som zakomentovane debug vypisy pre debugovanie rekurize, v buducnosti pri hlbsom komplexnejsom nestingu bude
# mozno vhodne zaviest aj max_recurse_depth parameter
# napr: rename_keys(data, ["ability_id", "ability_name", "True", "False"], ["id", "name", "usage_winners", "usage_loosers"])
def rename_keys(nest, keys_before: list, keys_after: list):
    # nest musi byt bud list alebo dict, inak je vrateny v povodnom stave
    if isinstance(nest, list): # rekurzia do listov
        for i, field in enumerate(nest):
            nest[i] = rename_keys(field, keys_before, keys_after)
    elif isinstance(nest, dict): # aplikovanie zmien v dictoch
        new_nest = dict()
        for key in nest:
            lkey = str(key).lower() # konverzia na lowercase string pre kontrolu
            if (lkey in keys_before):
                # index na ktorom sa v keys_before kluc nasiel je rovnaky ako index noveho kluca v keys_after
                # nastavenie new_nest[new_key] na hodnotu predchadzajuceho => premenovanie
                # povodne som chcel jednoduchy .pop, ale python potrebuje aby sa kluce pocas iteracii nemenili,
                # takze cely obsah dictu sa musi premiestnit do noveho
                if (isinstance(nest[key], dict) or isinstance(nest[key], list)):
                    # rekurzia do hodnot dictu tiez ak su podporovane
                    # print(lkey + " is dict or list and also renamed to " + keys_after[keys_before.index(lkey)])
                    # print("[recurse]")
                    new_nest[keys_after[keys_before.index(lkey)]] = rename_keys(nest[key], keys_before, keys_after)
                    # print("[recurse end]")
                else:
                    # ak tu nie je viac podporovaneho nestingu, jednoducho prirad hodnotu
                    # print(lkey + " is renamed to " + keys_after[keys_before.index(lkey)])
                    new_nest[keys_after[keys_before.index(lkey)]] = nest[key]
            else:
                if (isinstance(nest[key], dict) or isinstance(nest[key], list)):
                    # rekurzia do hodnot dictu tiez ak su podporovane
                    # print(lkey + " is dict or list not found in keys_before to be renamed")
                    # print("[recurse]")
                    new_nest[key] = rename_keys(nest[key], keys_before, keys_after)
                    # print("[recurse end]")
                else:
                    # ak tu nie je viac podporovaneho nestingu, jednoducho prirad hodnotu
                    # print(lkey + " is not found in keys_before to be renamed")
                    new_nest[key] = nest[key]
        nest = new_nest
    return nest