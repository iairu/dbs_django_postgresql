from django.db import models, connections


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
            a_entry[new_group].append(tmp)
            for x in will_group: a_entry.pop(x) # Odobranie povodnej formy uz agregovanych casti
    if (a_keyval != None): a_list.append(a_entry) # Treba ulozit poslednu agregaciu
    return a_list # Navrat "agregovanych" "de-duplikovanych" prvkov